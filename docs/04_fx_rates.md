# 4. Exchange rates — fx_rates

**Goal:** get the EUR↔RON exchange rate for every date the orders use, so RON orders can be converted
to EUR.

**What happens:**
- Reads the distinct dates needed from `orders_clean` (about 12 dates, 2026-08-23 → 2026-09-03).
- For each date, asks frankfurter.dev for the EUR→RON rate.
- The API is smart: for a **weekend/holiday** it returns the nearest previous business day's rate, and
  for a **future date** it returns the latest known rate — so we always get the "most appropriate rate
  for the date" without extra logic.
- Saves it as `fx_rates` (one EUR row = 1.0 and one RON row per date).

**Result:** 24 rows (12 dates × 2 currencies), RON around 5.25.

**Note on the daily change:** because future dates return today's latest rate, re-running each day
updates those future-date rates as the real dates arrive — this is the "simulated change" in the
challenge, and it flows into the two final tables.
