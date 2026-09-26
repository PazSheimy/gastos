# Gastos

Sort a bank or credit-card statement into spending categories, on your phone, without uploading it anywhere.

Open the page, pick your bank, choose the CSV you downloaded from the bank, and you get:

- total spent, split into personal and business
- every category with its monthly average and an optional budget
- a month-by-month chart
- the full transaction list, where you can fix a category and it applies to that merchant everywhere
- a download of the sorted transactions and a monthly summary, as CSV

Everything runs in the browser. There is no server and nothing is stored, except the category choices and budgets you make, which stay in your own browser and can be forgotten with one tap.

Works with CSV exports from Citi, Discover, Capital One, Truist, Chase, American Express, Bank of America and Wells Fargo, and with most other banks' CSVs.

## Files

- `docs/index.html` is the website. GitHub Pages serves it from the `docs` folder.
- `gastos.html` is the source of the page.
- `build_site.py` rebuilds `docs/index.html` from `gastos.html`. Run it after editing the source.
