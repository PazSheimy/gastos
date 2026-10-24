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
the STOCK Act. Pick a period (newest filing day, 7, 14, 30 or 90 days), filter by side,
party, trade size or a search, and read it four ways: by stock (money in and out per ticker,
using the midpoint of each reported range), by day (every filing as it was posted), by member,
and a "worth a look" list built from simple rules (several members on the same side, members
on opposite sides, trades over $250,000, one member trading a name three times or more).
Every row links to the original filing. Link straight to it with `#congress`.

The data is one public file, `docs/data/congress-trades.json`, rebuilt once a day by a
GitHub Action (`.github/workflows/congress.yml`) that runs `congress/fetch_trades.py`:
it reads the House Clerk's yearly filing index, downloads each new Periodic Transaction
Report PDF, parses the transactions table, adds party and district from the
`unitedstates/congress-legislators` project, and keeps the last 90 days of filings.
Paper (scanned) filings are listed but have no trades. Senate filings are not included:
the Senate disclosure site does not allow scripted access. To refresh by hand:

    pip install requests pdfplumber
    python congress/fetch_trades.py

## Files

- `docs/index.html` is the website. GitHub Pages serves it from the `docs` folder.
- `gastos.html` is the source of the page.
- `build_site.py` rebuilds `docs/index.html` from `gastos.html`. Run it after editing the source.
