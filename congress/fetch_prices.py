"""Daily closing prices for every ticker in congress-trades.json, plus SPY and the
copy-trade ETFs NANC and KRUZ, written as one compact JSON the web page reads.

Source: Yahoo Finance's chart endpoint (the same one the yfinance library uses).
It needs no key but is not an official API; if it ever stops working, swap the
`fetch_series` function for another daily-close source and keep the output shape.

Output shape (docs/data/prices.json):
    {"asof": "2026-10-24", "dates": ["2026-07-21", ...],      # SPY trading days
     "closes": {"SPY": [...], "NVDA": [...]},                   # aligned to dates, null = no close
     "missing": ["XYZ"]}                                        # tickers Yahoo did not know

    python congress/fetch_prices.py            # reads docs/data/congress-trades.json
    python congress/fetch_prices.py --pad 7    # days of prices before the earliest trade
"""
import argparse, datetime as dt, json, os, sys, time
from zoneinfo import ZoneInfo

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TRADES = os.path.join(ROOT, "docs", "data", "congress-trades.json")
OUT = os.path.join(ROOT, "docs", "data", "prices.json")
EXTRA = ["SPY", "NANC", "KRUZ"]
NY = ZoneInfo("America/New_York")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) gastos-congress/0.1"}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def yahoo_symbol(t):
    return t.replace(".", "-")


def fetch_series(ticker, start, end, tries=3):
    """Return {date: adjusted close} for one ticker, or None if Yahoo does not know it."""
    p1 = int(dt.datetime.combine(start, dt.time(), tzinfo=NY).timestamp())
    p2 = int(dt.datetime.combine(end + dt.timedelta(days=1), dt.time(), tzinfo=NY).timestamp())
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{yahoo_symbol(ticker)}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplit"
    for i in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=60)
        except requests.RequestException as e:
            log("  error", ticker, e); time.sleep(2 * (i + 1)); continue
        if r.status_code == 404:
            return None
        if r.status_code == 429:
            log("  429, waiting"); time.sleep(15 * (i + 1)); continue
        if r.status_code != 200:
            log("  http", r.status_code, ticker); time.sleep(2 * (i + 1)); continue
        try:
            res = r.json()["chart"]["result"]
        except Exception:
            return None
        if not res:
            return None
        res = res[0]
        ts = res.get("timestamp") or []
        ind = res.get("indicators", {})
        adj = (ind.get("adjclose") or [{}])[0].get("adjclose")
        close = (ind.get("quote") or [{}])[0].get("close")
        vals = adj if adj else close
        if not ts or not vals:
            return {}
        out = {}
        for t, v in zip(ts, vals):
            if v is None:
                continue
            d = dt.datetime.fromtimestamp(t, NY).date().isoformat()
            out[d] = round(float(v), 4 if v < 1 else 2)
        return out
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", default=TRADES)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--pad", type=int, default=7)
    ap.add_argument("--sleep", type=float, default=0.25)
    args = ap.parse_args()

    trades = json.load(open(args.trades, encoding="utf-8"))
    tickers = sorted({t["ticker"] for t in trades["trades"] if t.get("ticker")})
    dates = [t["date"] for t in trades["trades"] if t.get("date")]
    start = dt.date.fromisoformat(min(dates)) - dt.timedelta(days=args.pad) if dates else dt.date.today() - dt.timedelta(days=100)
    end = dt.date.today()
    want = EXTRA + [t for t in tickers if t not in EXTRA]
    log(len(want), "tickers from", start, "to", end)

    series, missing = {}, []
    for i, tk in enumerate(want):
        s = fetch_series(tk, start, end)
        if s is None:
            missing.append(tk)
        elif s:
            series[tk] = s
        else:
            missing.append(tk)
        if (i + 1) % 50 == 0:
            log(f"  {i + 1}/{len(want)} done, {len(missing)} missing")
        time.sleep(args.sleep)

    if "SPY" not in series:
        log("no SPY series; giving up"); sys.exit(1)
    cal = sorted(series["SPY"].keys())
    closes = {tk: [s.get(d) for d in cal] for tk, s in series.items()}
    out = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "asof": cal[-1],
           "source": "Yahoo Finance chart endpoint, adjusted close", "dates": cal, "closes": closes, "missing": missing}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
    log("wrote", args.out, f"{len(cal)} days x {len(closes)} tickers, missing {len(missing)}: {missing[:12]}")


if __name__ == "__main__":
    main()
