# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "b6fe96ce-4f8c-4874-9df9-163febd640bb",
# META       "default_lakehouse_name": "lh_orders",
# META       "default_lakehouse_workspace_id": "67987c73-aa85-43a2-9469-84f74ade792f",
# META       "known_lakehouses": [
# META         {
# META           "id": "b6fe96ce-4f8c-4874-9df9-163febd640bb"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# ## Country Revenue Summary — country_category_revenue
# 
# Purpose: show total EUR revenue by country for Books and Electronics, keeping only the
# countries above €40,000.
# 
# | Step | What it does | Result |
# |------|--------------|--------|
# | 1 | Keep only Books and Electronics orders, completed only | relevant orders |
# | 2 | Convert each order to EUR (line_total ÷ rate) using its fx_reference_date | amounts in EUR |
# | 3 | Sum revenue per country | one total per country |
# | 4 | Keep only countries whose total is over €40,000 (HAVING) | small countries dropped |
# | 5 | Rank highest revenue first | ordered list |
# 
# **Result:**
# 
# | country | revenue_eur |
# |---------|-------------|
# | RO | 146,608.56 |
# | HU | 40,823.50 |
# 
# Countries below the threshold were excluded: DE (~€38,333) and BG (~€32,254).
# 
# ### Conclusion
# This shows where the Books and Electronics business is strongest. Romania is by far the biggest
# market, and Hungary just clears the €40,000 bar. Germany and Bulgaria have real sales too but fall
# under the threshold, so they're left out. The €40,000 cut-off does real work here — it keeps the
# two meaningful markets and filters out the smaller ones.
# 
# Note: the exact figures depend on the exchange rate at run time, so they may shift slightly day to
# day; the set of qualifying countries (RO, HU) is stable.


# CELL ********************

# MAGIC %%sql
# MAGIC -- Total EUR revenue by country, only for Books or Electronics orders, keeping just the countries whose combined revenue is over €40,000, ranked highest first. 
# MAGIC -- Completed orders only (consistent with customer spend — refunds aren't revenue).
# MAGIC -- EUR revenue per country for Books & Electronics, only countries above 40,000, ranked.
# MAGIC -- The project asks for this specific breakdown.
# MAGIC -- same EUR conversion (line_total / rate_to_eur); filter categories; sum per country.
# MAGIC --      HAVING filters AFTER grouping (WHERE filters rows before; HAVING filters the totals).
# MAGIC -- One row per qualifying country, highest revenue first.
# MAGIC CREATE OR REPLACE TABLE country_category_revenue AS
# MAGIC SELECT
# MAGIC   o.country,
# MAGIC   ROUND(SUM(o.line_total / f.rate_to_eur), 2) AS revenue_eur
# MAGIC FROM orders_clean o
# MAGIC JOIN fx_rates f
# MAGIC   ON  f.fx_date  = o.fx_reference_date
# MAGIC   AND f.currency = o.currency
# MAGIC WHERE o.status = 'completed'
# MAGIC   AND o.category IN ('Books', 'Electronics')
# MAGIC GROUP BY o.country
# MAGIC HAVING SUM(o.line_total / f.rate_to_eur) > 40000
# MAGIC ORDER BY revenue_eur DESC

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Shows the final country/category revenue table.
# MAGIC -- Only countries over 40,000, ranked highest first.
# MAGIC SELECT * FROM country_category_revenue

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }
