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

# ## Data Check Summary — verifying the pipeline output
# 
# Purpose: after each pipeline run, confirm the output tables are complete and correct — not just
# that the job "ran", but that the data is trustworthy.
# 
# | # | Check | What it confirms | Result |
# |---|-------|------------------|--------|
# | 1 | fx_rates count & date range | all needed rates are present (24 rows, 2026-08-23 → 2026-09-03) | pass |
# | 2 | customer count & total | customer_spend_eur is populated with sane numbers (1,866 customers, ~€713,984) | pass |
# | 3 | country revenue rows | country_category_revenue holds the qualifying countries (RO, HU) | pass |
# | 4 | null / negative spend | no missing customer ids and no negative totals (€0 is allowed = free/promo) | pass (0, 0) |
# | 5 | FX coverage | every order's date+currency has a matching exchange rate (nothing dropped in conversion) | pass (0 missing) |
# 
# ### Conclusion
# All checks pass, so the output is verified accurate. Check 5 is the most important for accuracy —
# it guarantees no order was silently lost when converting to EUR. Check 4 also surfaced a real
# edge case: one customer with €0 spend, which traced back to the deliberate decision to keep
# free/promo (zero-price) items — so the check was refined to flag only negative totals, since €0
# is a valid value. These checks turn "the job ran" into "the numbers are correct", and can be run
# automatically as the final step of the daily pipeline so any bad result is caught immediately.


# CELL ********************

# MAGIC %%sql
# MAGIC -- expect: 24 rows, dates 2026-08-23 to 2026-09-03
# MAGIC SELECT COUNT(*) AS rows, MIN(fx_date) AS first_date, MAX(fx_date) AS last_date
# MAGIC FROM fx_rates

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- expect: ~1866 customers, total around 713,984 (may drift a few EUR if today's rate changed)
# MAGIC SELECT COUNT(*) AS customers, ROUND(SUM(total_spend_eur), 2) AS grand_total_eur
# MAGIC FROM customer_spend_eur

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- expect: RO and HU, both over 40,000, ranked
# MAGIC SELECT * FROM country_category_revenue

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- expect: all zeros (no missing ids, no negative spend; €0 is allowed = free/promo items)
# MAGIC SELECT
# MAGIC   SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS null_customers,
# MAGIC   SUM(CASE WHEN total_spend_eur < 0 THEN 1 ELSE 0 END) AS bad_totals
# MAGIC FROM customer_spend_eur

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- expect: 0 -> every order's date+currency has a matching exchange rate (nothing dropped in conversion)
# MAGIC SELECT COUNT(*) AS orders_missing_a_rate
# MAGIC FROM (SELECT DISTINCT fx_reference_date, currency FROM orders_clean) o
# MAGIC LEFT JOIN fx_rates f
# MAGIC   ON f.fx_date = o.fx_reference_date AND f.currency = o.currency
# MAGIC WHERE f.fx_date IS NULL

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Runs the data-quality checks and reads the result into one row `r`.
# We need the numbers in Python so we can send them out as a report.
#  missing_rates & negatives should be 0; customers ~1866; countries = 2.
r = spark.sql("""
  SELECT
    (SELECT COUNT(*) FROM orders_clean o                                    -- FX coverage check:
       LEFT JOIN fx_rates f ON f.fx_date=o.fx_reference_date AND f.currency=o.currency
       WHERE f.fx_date IS NULL) AS missing_rates,                           -- orders with no matching rate (want 0)
    (SELECT COUNT(*) FROM customer_spend_eur WHERE total_spend_eur < 0) AS negatives,  -- negative totals (want 0)
    (SELECT COUNT(*) FROM customer_spend_eur) AS customers,                 -- how many customers
    (SELECT COUNT(*) FROM country_category_revenue) AS countries            -- qualifying countries
""").first()

# Returns the report to the pipeline so the Teams activity can post it.
# notebookutils.notebook.exit is the only way to pass a value out to the pipeline.
notebookutils.notebook.exit(f"Data quality — missing_rates={r.missing_rates}, negatives={r.negatives}, customers={r.customers}, countries={r.countries}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
