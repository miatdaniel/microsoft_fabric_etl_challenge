# Challenge — "Making the Pipeline — Behind the scenes"

*A walkthrough of the whole build*

> **On AI usage:** the whole project — code, SQL, the pipeline, and this write-up — was built with **GitHub Copilot (chat)** as a pair-programmer. It suggested; I reviewed, decided, and verified. Where its first idea was wrong or over-complicated, I changed it.

---

## What was asked

A small but complete data pipeline: **ingest** orders from an API, **clean** them, pull daily **exchange rates**, produce a **customer-spend-in-EUR** table and a **country/category revenue** table (Books + Electronics, only countries over €40,000), **automate** the daily refresh, and write a short **summary**.

---

## The stack, and why

Everything runs in **Microsoft Fabric** — already had Fabric capacity enabled, and it keeps storage, notebooks, and scheduling in one place. It also runs both **SQL** and **Python**.

Inside Fabric I made a few choices:
- **Lakehouse over Warehouse.** A Lakehouse keeps everything as Delta tables and lets me drive transforms from notebooks with Spark SQL — the natural fit when the logic lives in notebooks.
- **Notebooks for the work.** SQL does the cleaning and the maths; Python appears in exactly two spots — the two API calls — and nowhere else.
- **A Data Pipeline for orchestration** — the thing that runs it all on a schedule.

I kept the code simple and readable on purpose: no heavy libraries, plain SQL, straightforward Python.

**Naming conventions** (for consistency): lowercase, descriptive, prefixed by type. The Lakehouse is `lh_orders`; the notebooks are `notebook_ingest_orders_raw`, `notebook_clean_orders`, `notebook_fx_rates`, `notebook_customer_spend`, `notebook_country_revenue`, and `notebook_data_check_after_pipeline_run`; the pipeline is `pipeline_daily_refresh`; and the tables keep the exact names the brief asked for (`orders_raw`, `orders_clean`, etc.).

---

## How it was built, step by step

### 1. Ingest — land the raw data as-is
A notebook calls the orders API, which pages 1,000 rows at a time, so it loops until the pages run out. It stores **every value as text** at this stage — on purpose, because the API returns some numbers as integers and some as decimals in the same column, and forcing types too early causes errors. Types are applied later, during cleaning. **Result: 9,268 rows in `orders_raw`.**

### 2. Profile — look before touching
A separate, read-only notebook checks the raw data *before* anything is changed. It counted duplicates, listed the status values (spotting a `test` status), tallied missing values, checked quantity/price ranges, and bucketed the date formats. It also answered a key question — **what makes a row unique?** No single column does; a row is identified by **`order_id` + `sku`** together (one product line per order). `customer_id` repeats by design (one customer, many orders), so it's a grouping key, not a unique key.

### 3. Clean — quarantine, don't delete
Instead of deleting bad rows, I moved each to a **quarantine table** (`orders_quarantine`) tagged with a reason. Nothing is lost, everything is reviewable, and `clean + quarantine` adds back up to the original 9,268. The clean table shrinks one issue at a time:

| After removing… | Rows quarantined | `orders_clean` now |
|---|---|---|
| start | — | 9,268 |
| duplicate rows | 183 | 9,085 |
| test orders | 97 | 8,988 |
| missing category | 77 | 8,911 |
| missing customer id | 96 | 8,815 |
| invalid quantity (≤ 0) | 161 | 8,654 |
| placeholder price (999999) | 13 | **8,641** |

Quarantine breakdown (627 total): duplicate 183 · invalid quantity 161 · test 97 · missing customer id 96 · missing category 77 · placeholder price 13.

A few decisions worth naming:
- **No recovery (yet).** Missing category/customer id could sometimes be reconstructed, but that needs business rules I don't have — so I quarantined them rather than guess. Deferred, not deleted.
- **Kept the odd-but-plausible.** Zero-priced rows stayed (free/promo is believable); only the obvious `999999` placeholder went.
- **Refunds stay, but don't count as spend.** They're valid history, so they live in `orders_clean`, but they're filtered out of the money tables — a refund isn't "spent."

Then the columns were converted to real types (numbers, dates), and the three different `order_ts` formats were folded into one timestamp. I used `TRY_CAST` rather than `CAST`, so a bad value becomes `NULL` instead of failing the whole query.

### 4. Exchange rates
A notebook reads the ~12 distinct dates from `orders_clean` and asks frankfurter.dev for the EUR→RON rate per date. Its single-date endpoint handles the awkward cases itself: a weekend returns the previous business day's rate, and a future date returns the latest known rate — which matches the "most appropriate rate for the date" the brief asked for, with no extra logic on my side. **Result: `fx_rates`, 24 rows** (EUR = 1.0 and a RON rate per date).

### 5. Customer spend in EUR
Join `orders_clean` to `fx_rates` on the order's `fx_reference_date` + currency, then convert with one formula: `line_total / rate`. EUR rows divide by 1.0 (unchanged); RON rows divide by ~5.25. Sum per customer, completed orders only. **Result: 1,866 customers, ≈ €713,984.79.**

### 6. Country / category revenue
Filter to Books + Electronics (completed), convert to EUR, group by country, and keep only countries over €40,000 using **`HAVING`, not `WHERE`**. `WHERE` filters individual rows *before* grouping; `HAVING` filters the *grouped totals*, which is what "over €40,000" is. **Result: RO €146,608.56, HU €40,823.50.** Germany (~€38.3k) and Bulgaria (~€32.3k) are real markets but fall just under the bar, so they're excluded.

### 7. Data-quality check
A final notebook checks the *output*, not just that the job ran. The main check is **FX coverage** — does every order have a matching rate? If a date/currency were missing, those orders would drop out of the join and understate the totals. It also checks for negative totals and sane row counts, and returns a short report.

### 8. Automate — the daily pipeline
`pipeline_daily_refresh` chains the steps, each running only **on success** of the previous:
`fx_rates → customer_spend → country_revenue → data_quality_check → send report to Teams`.
Ingest and cleaning sit *outside* the daily run because `orders_raw` is static — re-pulling and re-cleaning it daily adds nothing. The only thing that changes day to day is the FX rates (some `fx_reference_date`s are in the future), which then flow into the two money tables.

A few practical settings: every step has a **Teams failure alert**; the FX step has a **retry** (2 attempts, 90s apart) because it calls the internet; and every run rebuilds its tables from scratch (a full refresh), so re-running just reproduces the same result — no double-counting or half-finished state.

At real scale, I'd swap the full refresh for **incremental processing** — only touch new/changed rows. In practice: keep a **watermark** (the latest `order_ts` already loaded), pull only rows newer than that, and **`MERGE`** them into the existing tables (update matches, insert new ones) instead of rebuilding — with **date-partitioned** tables so each run only touches the new slice.

**Confirmed live:** the daily schedule fires and posts the report to Teams each day — `missing_rates=0, negatives=0, customers=1866, countries=2`.

---

## The monitoring report — a couple of detours worth noting

Getting the daily report into Teams took a couple of tries:
- I first tried a **Lookup** activity to query the Lakehouse and feed the numbers to Teams — but querying a Lakehouse directly in a Lookup is still a preview feature, so it wasn't available.
- After looking at the SQL analytics endpoint and a Script activity, I settled on the simplest reliable route: the data-check **notebook computes the report and returns it as its exit value**, and the Teams activity reads that value. One line of Python to hand it off; the rest is configuration.
- The Teams message also stamps the current date, so each one reads like "This is today's report (2026-08-27): …".

It's a small addition, but it means the daily message shows the actual numbers, not just that the job finished.

---

## Issues I hit, and how I fixed them

1. **"Cannot merge type Double and Long" on load** — mixed int/decimal in one column. → Land everything as **text**, cast later.
2. **Duplicates weren't being removed** — my first dedup rebuilt the clean table from a temporary view *of itself* (reading and overwriting the same object), which the engine won't do reliably, so the row count stayed 9,268 instead of 9,085. → **Materialise a helper table first**, then rebuild from it.
3. **A flagged "bad total" that was fine** — the quality check caught a €0-spend customer. It was someone who only bought free items — a valid €0, tracing back to the "keep zero-priced rows" decision. → Keep the customer; change the check to flag only *negative* totals.
4. **Pipeline couldn't run the notebooks — "Forbidden / insufficient permissions"** — the run identity lacked workspace access. → Enable the **workspace identity**, grant it Contributor, re-create the connection so it binds to the active identity.
5. **Email alerts failed — "MailboxNotEnabledForRESTAPI"** — the Outlook connector can't reach an on-prem mailbox, and re-logging in (or a gateway) doesn't help. → Switch alerts to **Teams**, then confirm it works by **forcing a step to fail** and watching the alert arrive.
6. **Couldn't connect Fabric to GitHub** — the provider was off at the tenant level, and my admin role was **PIM-eligible (dormant)**, so I couldn't change the setting. → **Activate the role via PIM**, wait for it to sync, enable the tenant setting, connect the workspace.

---

## Results

- **orders_raw** 9,268 → **orders_clean** 8,641 + **orders_quarantine** 627 (reconciles)
- **fx_rates** 24 rows (EUR + RON)
- **customer_spend_eur** — 1,866 customers, ≈ **€713,984.79**
- **country_category_revenue** — **RO €146,608.56**, **HU €40,823.50**
- **Automation** — daily pipeline live, posting a verified data-quality report to Teams every day.
