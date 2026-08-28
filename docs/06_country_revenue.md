# 6. Country revenue — country_category_revenue

**Goal:** show total EUR revenue by country for Books and Electronics, keeping only countries above
€40,000.

**What happens:**
- Keeps only **Books** and **Electronics** orders, completed only.
- Converts each to EUR (same `line_total / rate`).
- Sums revenue per country.
- Keeps only countries whose total is over **€40,000** (a `HAVING` filter, which filters the grouped
  totals — different from `WHERE`, which filters individual rows).
- Ranks highest revenue first.

**Result:**

| country | revenue_eur |
|---|---|
| RO | 146,608.56 |
| HU | 40,823.50 |

Germany (~€38,333) and Bulgaria (~€32,254) have real sales but fall below the €40,000 cutoff, so
they're excluded.

**Conclusion:** shows where the Books/Electronics business is strongest — Romania dominates, Hungary
just clears the bar. The €40,000 threshold does real work, separating the two meaningful markets from
the smaller ones. (Exact figures shift slightly with the daily exchange rate; the set of qualifying
countries stays the same.)
