# Writeup

## Data issues in `orders_raw`, how I handled them, and why

The raw data had 9,268 rows with several quality issues. Rather than deleting bad rows, I moved each to a **quarantine table** (`orders_quarantine`) tagged with a reason — so nothing is lost and everything can be reviewed later. `clean + quarantine` adds back up to the original 9,268.

- **183 duplicate rows** → kept one copy. Only *exact full-row* duplicates were removed, so genuine repeat orders (which differ in at least one field) are never lost.
- **97 `test` orders** → dropped (internal tests, not real sales).
- **77 missing categories** and **96 missing customer ids** → quarantined, **not** guessed. Recovering them needs business rules I don't have, so I deferred the decision rather than invent values.
- **161 zero/negative quantities** and **13 placeholder `999999` prices** → dropped (invalid).
- **Zero-priced rows** → **kept** (plausible free/promo items — no evidence they're wrong).
- **Three different date formats** in `order_ts` → standardised into one timestamp.
- **Refunded orders** → kept in `orders_clean` (valid history) but **excluded** from spend/revenue, because a refund isn't money "spent".

Result: `orders_clean` = 8,641 rows, `orders_quarantine` = 627 rows.

## How I'd monitor this in production (and catch a silent failure)

Monitoring is layered:
- **Per-step failure alerts** to Teams — if any step fails, I'm notified which one, and downstream steps are skipped so nothing runs on bad data.
- **The pipeline Monitor** shows every run's status and history.
- **A data-quality check** runs at the end and validates the *data*, not just that the job ran — most importantly that every order has a matching exchange rate (so no orders are silently dropped), plus no negative totals and sane row counts. It posts a **daily report to Teams**.

For a *silent* failure — a job that "succeeds" but produces wrong numbers, or doesn't run at all — the daily report is the safety net: if the numbers look wrong, or the report simply **doesn't arrive**, that's the signal. At larger scale I'd add a **dead-man's-switch** that alerts if no successful run happens within 24 hours.

*(Note: I first set up email alerts, but the Outlook connector failed because the mailbox is hosted on-premises; I switched to Teams, which works, and tested it by forcing a step to fail.)*

## AI usage — tools, and what I kept vs. changed

**Tool:** GitHub Copilot (chat), used throughout — the code, SQL, pipeline, and this write-up.

**Kept:** the overall approach (profile the data first, verify every step against the expected numbers), and the generated code/SQL once I had read it.

**Changed or owned myself:**
- Every cleaning **decision** was mine, checked against the real data (quarantine-not-delete, no-recovery, completed-only for spend, keeping €0/promo items).
- I kept the code simple and readable — no heavy libraries, minimal Python, plain SQL.
- I caught and fixed a real **bug** in the AI's first cleaning approach: the duplicate-removal step rebuilt `orders_clean` from a temporary *view of itself*, which meant reading and overwriting the same table at once — so the duplicates were never actually removed (the row count stayed 9,268 instead of 9,085). The verification step flagged it, and the fix was to materialise a separate helper table first, then rebuild from that.
- I worked through every environment issue (workspace permissions, Outlook → Teams, GitHub access) rather than accepting the first suggestion.
