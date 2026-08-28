# 2. Profiling — understanding orders_raw

**Goal:** look at the raw data and find every quality issue **before** changing anything. No data is
modified here — it's read-only.

**What was checked and found (9,268 rows):**

| Check | Finding |
|---|---|
| Table size | 9,268 rows |
| Duplicate rows | ~183 exact duplicates |
| Missing / blank values | customer_id missing in 103 rows, category in 79; other columns complete |
| Order statuses | completed, refunded (real) + 101 `test` (internal, not real sales) |
| Categories | 6 real categories + 79 rows with no category |
| Currencies & countries | currencies EUR, RON; countries RO, DE, HU, BG |
| Quantity | ranges from -3 to 3 → some zero/negative values |
| Price | ranges 0 to 999,999 → a fake 999,999 placeholder; some 0 prices |
| FX reference dates | 2026-08-23 → 2026-09-03, all valid |
| Unique identifier | no single column is unique; the key is `order_id` + `sku` |

**Conclusion:** the data is mostly good but has duplicates, test rows, some missing values,
out-of-range quantities, a placeholder price, and dates in the expected range. Each finding was
carried into the cleaning step as a specific decision.
