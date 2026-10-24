"""Probe what SEC EDGAR's free JSON APIs return, from a declared automated tool.

The SEC requires a User-Agent that names the tool and a contact, and allows at
most 10 requests a second. Run from GitHub Actions (workflow edgar-probe.yml).
"""
import collections, datetime as dt, json, os, re, time
import requests

CONTACT = os.environ.get("EDGAR_CONTACT", "85569927+PazSheimy@users.noreply.github.com")
H = {"User-Agent": f"gastos-congress {CONTACT}", "Accept-Encoding": "gzip, deflate"}


def get(u):
    r = requests.get(u, headers=H, timeout=60)
    time.sleep(0.2)
    if r.status_code != 200:
        print("  !!", r.status_code, u, re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))[:160])
    return r


r = get("https://www.sec.gov/files/company_tickers.json")
ct = r.json()
print(f"company_tickers.json: {len(ct)} companies, {len(r.content):,} bytes, cors={r.headers.get('access-control-allow-origin')}")
nvda = next(v for v in ct.values() if v["ticker"] == "NVDA")
cik = f"{nvda['cik_str']:010d}"
print("NVDA ->", nvda)

r = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
cf = r.json(); facts = cf["facts"].get("us-gaap", {})
print(f"companyfacts NVDA: {len(r.content):,} bytes, {len(facts)} us-gaap concepts")
for k in ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "NetIncomeLoss", "EarningsPerShareDiluted",
          "CommonStockSharesOutstanding", "Assets", "StockholdersEquity", "CashAndCashEquivalentsAtCarryingValue"]:
    if k in facts:
        units = facts[k]["units"]; u = next(iter(units))
        vals = [v for v in units[u] if v.get("form") in ("10-K", "10-Q")]
        last = sorted(vals, key=lambda v: v["end"])[-1]
        print(f"  {k:52s} {u:10s} {last['end']} = {last['val']:,} ({last['form']} {last.get('fp')}, filed {last['filed']}) ; {len(vals)} values back to {min(v['end'] for v in vals)}")

r = get(f"https://data.sec.gov/submissions/CIK{cik}.json")
sub = r.json(); rec = sub["filings"]["recent"]
print(f"submissions NVDA: {len(r.content):,} bytes, {len(rec['form'])} recent filings, older files: {len(sub['filings'].get('files', []))}")
since = (dt.date.today() - dt.timedelta(days=90)).isoformat()
forms = collections.Counter(f for f, d in zip(rec["form"], rec["filingDate"]) if d >= since)
print("  last 90 days by form:", forms.most_common(10))
# one Form 4: find the newest and fetch its XML listing
for f, d, acc, doc in zip(rec["form"], rec["filingDate"], rec["accessionNumber"], rec["primaryDocument"]):
    if f == "4":
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{doc}"
        r = get(url); print(f"  newest Form 4 {d}: {url} -> {r.status_code}, {len(r.content):,} bytes")
        m = re.findall(r"<(transactionCode|transactionShares|transactionPricePerShare|rptOwnerName)>\s*(?:<value>)?([^<]+)", r.text)
        print("   ", m[:8])
        break

r = get("https://data.sec.gov/api/xbrl/frames/us-gaap/Revenues/USD/CY2025.json")
if r.status_code == 200:
    fr = r.json(); print(f"frames Revenues USD CY2025: {len(fr['data'])} companies, {len(r.content):,} bytes")

for u in ["https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets",
          "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets",
          "https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets"]:
    r = requests.get(u, headers=H, timeout=60); time.sleep(0.2)
    zips = re.findall(r'href="([^"]+\.zip)"', r.text)
    print(f"dataset page {r.status_code} {u.rsplit('/', 1)[-1]}: {len(zips)} zip links, newest {zips[:1]}")

r = get("https://efts.sec.gov/LATEST/search-index?q=%22NVIDIA%22&forms=4&dateRange=custom&startdt=2026-09-01&enddt=2026-10-24")
print("full-text search Form 4 mentioning NVIDIA since Sep 1:", r.status_code, r.json().get("hits", {}).get("total") if r.status_code == 200 else "")
