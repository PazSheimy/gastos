# Gastos

Sort a bank or credit-card statement into spending categories, on your phone, without uploading it anywhere.

Open the page, pick your bank, choose the CSV you downloaded from the bank, and you get:

- total spent, split into personal and business
- every category with its monthly average and an optional budget
- a month-by-month chart
- the full transaction list, where you can fix a category and it applies to that merchant everywhere
- your trips, found from the statement itself: days of purchases away from home become a trip, together with the flights (matched by departure date) and the stays booked ahead
- an Excel download with a Trips sheet comparing every trip, one sheet per trip (by category, day by day, every purchase), a spending summary, all transactions and the monthly tables
- an Ask my CPA tick on any transaction: those collect under For my CPA, with your note as the question, and download as an Excel list with columns for her answer
- a download of the sorted transactions and a monthly summary, as CSV

Everything runs in the browser. There is no server and nothing is stored, except the category choices and budgets you make, which stay in your own browser and can be forgotten with one tap.

Works with CSV exports from Citi, Discover, Capital One, Truist, Chase, American Express, Bank of America and Wells Fargo, and with most other banks' CSVs.

## Money plan

The header switch opens a second tool, also fully in the browser: enter what you earn
(hourly, monthly or yearly), optionally let it estimate 2026 US taxes (federal brackets and
standard deduction, Social Security, Medicare, a flat state rate), and the take-home pay is
split 55% needs, 5% fun, 10% invest every month, 15% savings and goals, 15% long-term
investing. If a statement is loaded, it compares your real needs and fun spending to the plan.
Link straight to it with `#plan`.

## Notes tab

A third tab, Notes, is a personal notebook of lessons read in books and research, with a
'not financial advice' banner. Each lesson is one entry in the `NOTES` array in `gastos.html`
(title, takeaway, tags, HTML body); adding a lesson is adding one entry. Link straight to it
with `#notes`, or to one note with `#note-<id>`.

## Congress tab

A fourth tab, Congress, shows the stock trades that members of the US House report under
the STOCK Act. Pick a period (newest filing day, 7, 14, 30 or 90 days). A stats table
describes the period (trades with a ticker, different tickers, tickers outside the 50
largest companies, smallest-bucket trades, trades over $250,000, orders made in pieces,
members who filed); tap a row to open that slice. Filter by side, party, trade size, a
search, assets with a ticker only, or hide the 50 largest companies. Read it four ways:
by stock (money in and out per ticker, using the midpoint of each reported range), by day
(every filing as it was posted), members (with a scorecard), and a "worth a look" list
built from simple rules (several members on the same side, members on opposite sides,
orders over $250,000, one member trading a name on three or more days, a price that moved
15 points or more against SPY). Every row links to the original filing. Link straight to
it with `#congress`.

Pieces: when one member trades the same name, same side, same day in several lines
(usually one per account), the page shows one order with the combined range and a
"pieces" chip, and the rules count it once.

Prices: every trade shows the price change from the trade date to the latest close next
to SPY over the same days, and each member gets a scorecard (midpoint-weighted excess
return over SPY on buys, hit rate, and what their sells avoided). This is an estimate of
copying the trade, not the member's real return. The members view also compares SPY with
NANC and KRUZ, the ETFs that copy Democratic and Republican members' trades.

The data is two public files in `docs/data/`, rebuilt once a day by a GitHub Action
(`.github/workflows/congress.yml`):

- `congress-trades.json` from `congress/fetch_trades.py`: reads the House Clerk's yearly
  filing index, downloads each new Periodic Transaction Report PDF, parses the transactions
  table, adds party and district from the `unitedstates/congress-legislators` project, and
  keeps the last 90 days of filings. Paper (scanned) filings are listed but have no trades.
- `prices.json` from `congress/fetch_prices.py`: daily adjusted closes for every traded
  ticker plus SPY, NANC and KRUZ, from Yahoo Finance's chart endpoint (no key, but not an
  official API; the function to swap is `fetch_series`).

Senate filings are not included: the Senate disclosure site does not allow scripted access.
SEC EDGAR (company facts, Form 4 insider trades) is the planned next source; its site
currently refuses scripted requests from this machine and from GitHub's runners even with
the declared user agent the SEC asks for, so that is parked (see `congress/edgar_probe.py`).
To refresh by hand:

    pip install requests pdfplumber
    python congress/fetch_trades.py
    python congress/fetch_prices.py

## Files

- `docs/index.html` is the website. GitHub Pages serves it from the `docs` folder.
- `gastos.html` is the source of the page.
- `build_site.py` rebuilds `docs/index.html` from `gastos.html`. Run it after editing the source.
