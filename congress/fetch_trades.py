"""Pull Periodic Transaction Reports (stock trades) that members of the US House
report under the STOCK Act, and write them as one JSON file the web page reads.

Source: the House Clerk's public financial disclosure site. The yearly index
(2026FD.zip) lists every filing; each PTR is a text PDF that this script parses.
Nothing here is private: these filings are published for anyone to read.

    python congress/fetch_trades.py               # refresh docs/data/congress-trades.json
    python congress/fetch_trades.py --days 90     # how far back to keep filings (by filing date)
    python congress/fetch_trades.py --max-new 40  # cap downloads per run (useful while testing)

Runs daily from GitHub Actions (.github/workflows/congress.yml). Already-parsed
filings are kept from the previous JSON, so a run only downloads new PDFs.
"""
import argparse, datetime as dt, io, json, os, re, sys, time, zipfile

import requests
import pdfplumber

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DEFAULT = os.path.join(ROOT, "docs", "data", "congress-trades.json")
UA = {"User-Agent": "gastos-congress/0.1 (public STOCK Act disclosures reader; github.com/PazSheimy/gastos)"}
HOUSE_INDEX = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
HOUSE_PDF = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc}.pdf"
LEGISLATORS = "https://unitedstates.github.io/congress-legislators/legislators-current.json"
CACHE = os.environ.get("CONGRESS_CACHE")  # optional folder for downloaded PDFs while developing

DATE_RX = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
TYPE_RX = re.compile(r"^(P|S|E)$")
LABEL_RX = re.compile(r"^[A-Z](?:\s+[A-Z])*\s*(?::\s*(.*))?$")  # small-caps labels lose their lowercase glyphs
ASSET_RX = re.compile(r"^(.*?)\s*(?:\(([A-Z][A-Z0-9.\-/ ]{0,11})\))?\s*\[([A-Z]{2,3})\]\s*$")
MONEY_RX = re.compile(r"\$([\d,]+)")


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def get(url, tries=3, **kw):
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=60, **kw)
            if r.status_code == 200:
                return r
            log("  http", r.status_code, url)
        except requests.RequestException as e:
            log("  error", e)
        time.sleep(2 * (i + 1))
    return None


def iso(mdy):
    m, d, y = mdy.split("/")
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


# ---------- House index ----------
def house_index(years):
    rows = []
    for y in years:
        r = get(HOUSE_INDEX.format(year=y))
        if not r:
            log("index missing for", y)
            continue
        z = zipfile.ZipFile(io.BytesIO(r.content))
        txt = z.read(f"{y}FD.txt").decode("utf-8", "replace").splitlines()
        for line in txt[1:]:
            p = line.split("\t")
            if len(p) < 9 or p[4].strip() != "P":
                continue
            rows.append({"prefix": p[0].strip(), "last": p[1].strip(), "first": p[2].strip(), "suffix": p[3].strip(),
                         "state_dst": p[5].strip(), "year": p[6].strip(), "filed": iso(p[7].strip()), "doc": p[8].strip()})
    return rows


# ---------- House PDF parsing ----------
def rows_from_words(words, tol=3.0):
    """Group pdfplumber words into visual rows by their top coordinate.

    The form's small-caps labels (Filing Status, Subholding Of, Description...)
    come out as a capital letter followed by NUL glyphs, e.g. 'F\\x00\\x00\\x00'.
    A row containing such a word is a label row, not part of the asset text.
    """
    rows = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if rows and abs(rows[-1]["top"] - w["top"]) <= tol:
            rows[-1]["words"].append(w)
        else:
            rows.append({"top": w["top"], "words": [w], "label": False})
    for r in rows:
        r["words"].sort(key=lambda w: w["x0"])
        for w in r["words"]:
            if "\x00" in w["text"]:
                r["label"] = True
                w["text"] = w["text"].replace("\x00", "")
        r["words"] = [w for w in r["words"] if w["text"]]
        r["text"] = " ".join(w["text"] for w in r["words"])
    return [r for r in rows if r["words"]]


COLS = ["id", "owner", "asset", "type", "date", "notified", "amount", "cap"]
HEADER_WORDS = {"ID": "id", "Owner": "owner", "Asset": "asset", "Transaction": "type", "Date": "date",
                "Notification": "notified", "Amount": "amount", "Cap.": "cap"}


def find_columns(row):
    """From the table header row, return the x0 of each column, or None."""
    xs = {}
    for w in row["words"]:
        key = HEADER_WORDS.get(w["text"])
        if key == "date" and "date" in xs:
            continue
        if key and key not in xs:
            xs[key] = w["x0"]
    if not all(k in xs for k in ("asset", "type", "date", "amount")):
        return None
    xs.setdefault("id", 0)
    xs.setdefault("owner", xs["id"] + 1)
    xs.setdefault("notified", (xs["date"] + xs["amount"]) / 2)
    xs.setdefault("cap", 10_000)
    return xs


def split_columns(row, cols):
    out = {k: [] for k in COLS}
    bounds = sorted(((cols[k], k) for k in COLS), key=lambda t: t[0])
    for w in row["words"]:
        col = bounds[0][1]
        for x0, k in bounds:
            if w["x0"] >= x0 - 3:
                col = k
        out[col].append(w["text"])
    return {k: " ".join(v) for k, v in out.items()}


def parse_amount(text):
    text = text.replace("–", "-")
    nums = [int(n.replace(",", "")) for n in MONEY_RX.findall(text)]
    if not nums:
        return None, None
    if re.search(r"\bover\b", text, re.I) or text.strip().endswith("+"):
        return nums[0], None
    if "or less" in text.lower():
        return 0, nums[0]
    lo = nums[0]
    hi = nums[1] if len(nums) > 1 else None
    return lo, hi


def finish(t):
    """Clean one accumulated transaction into its final shape."""
    asset = re.sub(r"\s+", " ", t["asset"]).strip()
    m = ASSET_RX.match(asset)
    name, ticker, kind = (m.group(1), m.group(2), m.group(3)) if m else (asset, None, None)
    name = name.strip(" -")
    ticker = ticker.strip() if ticker else None
    if ticker and " " in ticker:
        ticker = None
    typ = re.sub(r"\s+", " ", t["type"]).strip()
    typ = {"P": "P", "S": "S", "E": "E", "S (partial)": "SP"}.get(typ, typ[:1] if typ else "")
    lo, hi = parse_amount(t["amount"])
    out = {"date": iso(t["date"]) if DATE_RX.match(t["date"]) else t["date"],
           "notified": iso(t["notified"]) if DATE_RX.match(t["notified"]) else t["notified"],
           "owner": t["owner"].strip() if t["owner"].strip() in ("SP", "DC", "JT") else "",
           "asset": name, "ticker": ticker, "kind": kind, "type": typ,
           "amount": re.sub(r"\s+", " ", t["amount"]).strip(), "lo": lo, "hi": hi}
    for k in ("status", "sub", "desc", "comment"):
        v = t.get(k, "").strip()
        if v:
            out[k] = v
    if t.get("cap", "").strip():
        out["cap"] = t["cap"].strip()
    return out


def parse_house_pdf(data):
    """Return (info, trades, is_paper). info has name/status/state_dst."""
    info, trades = {}, []
    cols, in_table, cur, last_label = None, False, None, None
    text_chars = 0
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=1.5, y_tolerance=3)
            text_chars += sum(len(w["text"]) for w in words)
            for row in rows_from_words(words):
                t = row["text"]
                if not info.get("name"):
                    m = re.match(r"Name:\s*(.+)$", t)
                    if m:
                        info["name"] = m.group(1).strip()
                        continue
                if "status" not in info:
                    m = re.match(r"Status:\s*(.+)$", t)
                    if m:
                        info["status"] = m.group(1).strip()
                        continue
                if "state_dst" not in info:
                    m = re.match(r"State/District:\s*(.+)$", t)
                    if m:
                        info["state_dst"] = m.group(1).strip()
                        continue
                c = find_columns(row)
                if c:
                    cols, in_table = c, True
                    continue
                if not in_table:
                    continue
                if t.startswith("* For the complete list of asset type"):
                    if cur:
                        trades.append(finish(cur)); cur = None
                    in_table = False
                    continue
                if t in ("Type Date Gains >", "$200?", "Type Date Gains > $200?") or t.startswith("Filing ID #") or t.startswith("Clerk of the House"):
                    continue
                if row["label"]:
                    if cur is None:
                        continue
                    key = {"F": "status", "S": "sub", "D": "desc", "C": "comment", "L": "location"}.get(t[0])
                    val = t.split(":", 1)[1].strip() if ":" in t else ""
                    if key:
                        cur[key] = (cur.get(key, "") + " " + val).strip()
                        last_label = key
                    continue
                parts = split_columns(row, cols)
                starts = TYPE_RX.match(parts["type"].split(" ")[0] if parts["type"] else "") and DATE_RX.match(parts["date"].split(" ")[0] if parts["date"] else "")
                if starts:
                    if cur:
                        trades.append(finish(cur))
                    cur = {"owner": parts["owner"], "asset": parts["asset"], "type": parts["type"],
                           "date": parts["date"], "notified": parts["notified"], "amount": parts["amount"], "cap": parts["cap"]}
                    last_label = None
                elif cur is not None and last_label:
                    # a description or comment that wrapped onto another line
                    cur[last_label] = (cur.get(last_label, "") + " " + t).strip()
                elif cur is not None:
                    # wrapped continuation of the current transaction
                    if parts["asset"]:
                        cur["asset"] += " " + parts["asset"]
                    if parts["amount"]:
                        cur["amount"] += " " + parts["amount"]
                    if parts["type"]:
                        cur["type"] += " " + parts["type"]
                    if parts["cap"]:
                        cur["cap"] += " " + parts["cap"]
                    if parts["owner"] and not cur["owner"]:
                        cur["owner"] = parts["owner"]
    if cur:
        trades.append(finish(cur))
    return info, trades, text_chars < 40


# ---------- legislators (party, chamber) ----------
def load_legislators():
    r = get(LEGISLATORS)
    if not r:
        return {}
    by_key = {}
    for p in r.json():
        term = p["terms"][-1]
        last = p["name"]["last"].lower()
        if term["type"] == "rep":
            key = ("H", last, term["state"], f"{int(term.get('district', 0)):02d}")
        else:
            key = ("S", last, term["state"], "")
        by_key[key] = {"party": term.get("party", "")[:1], "name": p["name"].get("official_full") or f"{p['name']['first']} {p['name']['last']}"}
    return by_key


def party_for(filing, legs):
    sd = filing.get("state_dst") or ""
    st, dist = sd[:2], sd[2:4]
    hit = legs.get(("H", filing["last"].lower(), st, dist))
    if hit:
        return hit["party"]
    # fall back: same last name and state, any district
    for (ch, last, s, d), v in legs.items():
        if ch == "H" and last == filing["last"].lower() and s == st:
            return v["party"]
    return ""


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--max-new", type=int, default=400)
    args = ap.parse_args()

    today = dt.date.today()
    since = today - dt.timedelta(days=args.days)
    years = sorted({since.year, today.year})

    prev = {"filings": [], "trades": []}
    if os.path.exists(args.out):
        try:
            prev = json.load(open(args.out, encoding="utf-8"))
        except Exception as e:
            log("could not read previous json:", e)
    have = {f["id"]: f for f in prev["filings"]}
    old_trades = {}
    for t in prev["trades"]:
        old_trades.setdefault(t["id"], []).append(t)

    log("House index for", years)
    index = [r for r in house_index(years) if r["filed"] >= since.isoformat()]
    log(len(index), "PTR filings since", since)
    legs = load_legislators()

    filings, trades, new = [], [], 0
    for r in sorted(index, key=lambda r: r["filed"], reverse=True):
        fid = "H" + r["doc"]
        if fid in have and not have[fid].get("err"):
            filings.append(have[fid]); trades.extend(old_trades.get(fid, []))
            continue
        if new >= args.max_new:
            if fid in have:
                filings.append(have[fid]); trades.extend(old_trades.get(fid, []))
            continue
        new += 1
        url = HOUSE_PDF.format(year=r["year"], doc=r["doc"])
        data = None
        cpath = os.path.join(CACHE, r["doc"] + ".pdf") if CACHE else None
        if cpath and os.path.exists(cpath):
            data = open(cpath, "rb").read()
        else:
            resp = get(url)
            if resp:
                data = resp.content
                if cpath:
                    open(cpath, "wb").write(data)
            time.sleep(0.4)
        name = " ".join(x for x in (r["first"], r["last"], r["suffix"]) if x)
        filing = {"id": fid, "ch": "H", "name": name, "party": party_for(r, legs), "state": r["state_dst"][:2],
                  "dist": r["state_dst"][2:], "filed": r["filed"], "url": url, "n": 0}
        if not data:
            filing["err"] = "download"; filings.append(filing); continue
        try:
            info, rows, paper = parse_house_pdf(data)
        except Exception as e:
            log("  parse failed", fid, e)
            filing["err"] = "parse"; filings.append(filing); continue
        if paper:
            filing["paper"] = True
        if info.get("name"):
            filing["name"] = re.sub(r"^(Hon\.|Mr\.|Mrs\.|Ms\.|Dr\.)\s+", "", info["name"]).strip()
        if info.get("status"):
            filing["status"] = info["status"]
        filing["n"] = len(rows)
        for t in rows:
            t["id"] = fid
        filings.append(filing); trades.extend(rows)
        log(f"  {fid} {filing['name']} {r['filed']} -> {len(rows)} trades" + (" (paper)" if paper else ""))

    filings.sort(key=lambda f: (f["filed"], f["id"]), reverse=True)
    out = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "days": args.days,
           "since": since.isoformat(),
           "sources": {"house": "https://disclosures-clerk.house.gov/FinancialDisclosure",
                       "senate": "https://efdsearch.senate.gov/search/",
                       "legislators": "https://github.com/unitedstates/congress-legislators"},
           "counts": {"filings": len(filings), "trades": len(trades), "paper": sum(1 for f in filings if f.get("paper")),
                      "errors": sum(1 for f in filings if f.get("err"))},
           "filings": filings, "trades": trades}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    log("wrote", args.out, out["counts"], "new downloads:", new)


if __name__ == "__main__":
    main()
