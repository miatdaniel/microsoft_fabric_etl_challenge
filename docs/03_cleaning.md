# 3. Cleaning — orders_clean (with quarantine)

**Goal:** turn the raw data into a trustworthy `orders_clean` table. Instead of deleting bad rows,
they are moved to a **quarantine table** (`orders_quarantine`) with a reason — so nothing is lost and
`clean + quarantine = 9,268`.

**Each step removes one problem (and quarantines it):**

| Step | Removes | Rows | Why |
|---|---|---|---|
| 1 | duplicate rows | 183 | keep one copy; only exact full-row duplicates are removed, so real orders are never lost |
| 2 | test orders | 97 | internal tests, not real sales |
| 3 | missing category | 77 | can't trust it; recovery left for later |
| 4 | missing customer id | 96 | can't attribute it; recovery left for later |
| 5 | invalid quantity (≤ 0) | 161 | an order can't have zero/negative items |
| 6 | placeholder price (999999) | 13 | obvious fake value |

Rows priced **0** were **kept** — plausibly free/promo items.

**Then:** the columns are converted to proper types (numbers, dates), and the three different date
formats in `order_ts` are standardised into one timestamp.

**Result:** `orders_clean` = 8,641 rows, `orders_quarantine` = 627 rows (together = 9,268).

**Key decisions:**
- Quarantine, don't delete — auditable and recoverable.
- Don't recover missing values yet — decision deferred pending business rules.
- Keep refunded orders in the clean table (valid history) but exclude them from spend/revenue later.
