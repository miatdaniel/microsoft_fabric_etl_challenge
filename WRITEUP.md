# Writeup

## Tools & approach
Built entirely in **Microsoft Fabric** — one **Lakehouse** (`lh_orders`), a set of **notebooks**
(Spark SQL for transforms, a little Python for the two API pulls), and a **Data Pipeline**
(`pipeline_daily_refresh`) on a daily schedule. I chose Fabric because the capacity was already
available (no extra cost), it keeps everything in one workspace, and it supports both SQL and
Python so the required skills are visible.

Throughout, I worked **profiling-first** (understand the data before changing it) and
**verified every step** against expected numbers, so issues were caught immediately.

---

## 1. Data issues found in `orders_raw`, how I handled them, and why

Source: **9,268 rows**. After cleaning: **8,641 rows** in `orders_clean`; the removed **627 rows**
were moved to a **quarantine table** (`orders_quarantine`) with a reason — not deleted.

| Issue | Rows | Decision | Why |
|---|---|---|---|
| Exact duplicate rows | 183 | quarantined (kept 1 copy) | only *full-row* duplicates removed, so genuine repeat orders (which differ in at least one field) are never lost |
| `status = 'test'` orders | 97 | quarantined | internal test orders, not real sales |
| Missing `category` | 77 | quarantined (**not** recovered) | recovery deferred pending business rules — I didn't want to guess |
| Missing `customer_id` | 96 | quarantined (**not** recovered) | same — can't attribute the order, decision deferred |
| Zero / negative `qty` | 161 | quarantined | an order can't have ≤ 0 items |
| Placeholder price `999999` | 13 | quarantined | obvious fake/sentinel value |
| Price `0` | 24 | **kept** | plausible free/promo items — no evidence it's wrong |
| `order_ts` in 3 formats (ISO, unix, dd/MM/yyyy) | ~all | standardised to one timestamp | consistency; anything unrecognised → NULL (and profiling flags unknown formats) |
| `refunded` orders | 399 | kept in `orders_clean`, **excluded** from spend/revenue | a refund isn't "spent"/revenue, but the record is still valid history |

**Key decisions & reasoning**
- **Quarantine instead of delete** — bad rows are preserved with a reason, so nothing is lost and
  they can be reviewed/recovered later. `clean + quarantine = 9,268` (reconciles exactly).
- **No recovery** of missing category/customer_id at this stage — deferred until the business
  intent is known, rather than guessing.
- **Completed orders only** for `customer_spend_eur` and `country_category_revenue` — "spent"/
  "revenue" means money that stayed, not refunds. (Including refunds would give a different total;
  I chose the stricter, defensible reading.)
- **FX conversion:** `amount_in_eur = line_total / rate_to_eur`. EUR rows have rate 1.0 (unchanged);
  RON rows are divided by the rate for that order's `fx_reference_date`. For weekend/holiday/future
  dates, frankfurter.dev automatically returns the most appropriate rate (prior business day, or the
  latest known), which matches the "most appropriate rate for the date" requirement.
- An automated data-quality check later **surfaced one €0-spend customer** — traced back to the
  deliberate decision to keep free/promo (€0-price) items. €0 is valid, so I kept the customer and
  refined the check to flag only *negative* totals. (A check catching a real edge case = working as
  intended.)

**Results:** `customer_spend_eur` = 1,866 customers, ≈ €713,984.79. `country_category_revenue` =
RO €146,608.56, HU €40,823.50 (DE ≈ €38.3k and BG ≈ €32.3k fall below the €40,000 cutoff).

---

## 2. How I'd monitor this in production (and catch a *silent* failure)

The daily pipeline (`pipeline_daily_refresh`) has layered monitoring:

1. **Per-step failure alerts** — every notebook step has a Teams "on-failure" notification, so if any
   step fails, I get a message naming that step (and downstream steps are skipped, not run on stale data).
2. **Pipeline Monitor** — Fabric's run history shows every run's status/timings.
3. **Data-quality check step** (`data_check_after_pipeline_run`) — runs at the end and verifies the
   *data*, not just that the job "ran": most importantly **FX coverage** (every order date+currency
   has a matching rate, so no order is silently dropped in conversion), plus no negative totals and
   sane row counts. It posts a **daily Teams report** with the numbers.
4. **Catching a silent failure** — a job can "succeed" but produce garbage, or not run at all. This is
   covered by: (a) the data-quality report arriving each day — if the numbers look wrong, or the
   report *doesn't arrive*, that's the signal; (b) the failure alerts; and (c) at scale I'd add a
   **dead-man's-switch** (alert if no successful run/report checks in within ~24h).

**Honest note:** I first wired failure alerts via Outlook email, but the connector failed with
`MailboxNotEnabledForRESTAPI` because the account's mailbox is on-premises (hybrid Exchange), which
the connector can't reach. I switched to **Teams**, which works with the corporate account, and
**tested it by forcing a step to fail** and confirming the alert arrived.

The design is **idempotent (full refresh)** — each run rebuilds tables from the untouched source, so
reruns never accumulate duplicates. `orders_raw` is static here, so the daily change comes only from
FX rates (some `fx_reference_date` values are in the future); at real scale I'd switch to
**incremental processing** (watermark + MERGE / date partitioning) so the daily job stays proportional
to new data.

---

## 3. AI usage

**Tool:** GitHub Copilot Chat (Claude) throughout.

**What I kept:**
- The overall architecture and the **profiling-first, verify-each-step** approach.
- Generated notebook/SQL after reading and understanding each piece.
- The quarantine-with-reasons cleaning pattern and the FX/EUR conversion logic.

**What I changed or verified myself:**
- Every cleaning **decision** was checked against the real data (e.g. confirmed the €0 total was
  free/promo, not an error; decided quarantine-not-delete and no-recovery deliberately).
- Simplified code to my comfort level — **no pandas**, minimal Python, plain readable SQL.
- Caught and fixed a real **bug** the AI's first cleaning approach hit: rebuilding a table from a
  temp view of *itself* (self-reference) left duplicates in place; the fix was to materialise an
  intermediate table.
- Discovered that frankfurter.dev's single-date endpoint **auto-resolves** weekend/future dates, which
  let me drop the carry-forward code entirely.
- Worked through real environment issues (workspace-identity permissions, PIM role activation for Git
  integration, Outlook→Teams) rather than accepting the first suggestion.
