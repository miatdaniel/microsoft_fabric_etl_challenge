# 1. Ingestion — orders_raw

**Goal:** pull all the orders from the source API and store them in the Lakehouse, unchanged.

**What happens:**
- Calls the orders API, sending the required apikey.
- The API only returns 1000 rows at a time, so it loops until it has collected all of them.
- Every value is stored as text at this stage, so mixed number/decimal columns don't cause errors
  (they're turned into proper numbers later, during cleaning).
- Saves everything into the `orders_raw` table.
- A check counts the rows to confirm the load worked.

**Result:** 9,268 rows loaded into `orders_raw` — matches the source total, so nothing was lost or
duplicated.
