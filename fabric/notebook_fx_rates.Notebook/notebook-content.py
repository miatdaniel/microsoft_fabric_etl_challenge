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

# ## 1. See what currencies and dates we need

# CELL ********************

# MAGIC %%sql
# MAGIC -- Lists the distinct currencies in the clean orders.
# MAGIC -- Tells us which currencies need converting to EUR (EUR needs no conversion).
# MAGIC SELECT DISTINCT currency FROM orders_clean ORDER BY currency

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Shows the earliest/latest fx_reference_date and how many distinct dates.
# MAGIC -- Tells us the date range of exchange rates to pull.
# MAGIC -- a first date, a last date, and a count of distinct dates.
# MAGIC SELECT
# MAGIC   MIN(fx_reference_date) AS first_date,
# MAGIC   MAX(fx_reference_date) AS last_date,
# MAGIC   COUNT(DISTINCT fx_reference_date) AS distinct_dates
# MAGIC FROM orders_clean

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# 
# | Result | Meaning |
# |--------|---------|
# | `first_date` = 2026-08-23 | the earliest date any order points to |
# | `last_date` = 2026-09-03 | the latest date any order points to |
# | `distinct_dates` = 12 | there are only 12 different dates in total |
# 
# This defines the exact date range of exchange rates we need to pull from frankfurter.dev
# (`start = first_date`, `end = last_date`). It also shows the job is small (12 dates), and that
# the last date is in the future — a hint that some dates won't have real market rates yet, so
# we'll carry forward the most recent known rate for those.

# MARKDOWN ********************

# ## 2. Pull the exchange rates from frankfurter.dev
# 
# For each date we need, we ask the API for the EUR->RON rate. The API is smart: for a weekend it
# returns the nearest previous business day's rate, and for a future date it returns the latest
# known rate. So we always get the "most appropriate rate for the date" without extra logic.

# CELL ********************

import requests  # to call the exchange-rate API

# 1. get the list of dates we need, from the clean orders
dates = [str(r[0]) for r in spark.sql(
    "SELECT DISTINCT fx_reference_date FROM orders_clean ORDER BY fx_reference_date"
).collect()]


# 2. for each date, ask the API for the EUR->RON rate
#    (weekends -> nearest business day; future dates -> latest rate; handled by the API)
rows = []
for d in dates:
    resp = requests.get(f"https://api.frankfurter.dev/v1/{d}?to=RON").json()
    ron_rate = resp["rates"]["RON"]
    rows.append((d, "EUR", 1.0))        # EUR is the base currency, always 1
    rows.append((d, "RON", ron_rate))   # the RON rate for this date


# 3. save as the fx_rates table (fx_date stored as a real date so it joins cleanly later)
df = spark.createDataFrame(rows, ["fx_date", "currency", "rate_to_eur"])
df = df.withColumn("fx_date", df.fx_date.cast("date"))
df.write.mode("overwrite").saveAsTable("fx_rates")
print("Saved fx_rates:", len(rows), "rows")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Shows the full fx_rates table.
# MAGIC -- one EUR (=1.0) and one RON row per date -> 24 rows (12 dates x 2 currencies).
# MAGIC SELECT * FROM fx_rates ORDER BY fx_date, currency

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# **Results observation:**
# 
# 2026-08-23 (Sunday) → 5.2563 (Friday's rate)
# 
# 2026-08-24 → 5.2504 (real Monday)
# 
# 2026-08-25 (today) → 5.2537
# 
# 2026-08-26 onward (future) → 5.2537 (today's rate carried forward — this will update as those dates arrive)
