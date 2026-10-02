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

## Files

- `docs/index.html` is the website. GitHub Pages serves it from the `docs` folder.
- `gastos.html` is the source of the page.
- `build_site.py` rebuilds `docs/index.html` from `gastos.html`. Run it after editing the source.
