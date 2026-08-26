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

# ## Data Profiling Summary — orders_raw
# 
# Purpose: understand the raw data and record findings only. No changes made, no decisions here.
# 
# | # | Step | What was checked | Finding |
# |---|------|------------------|---------|
# | 1 | Table size | number of rows | 9,268 rows |
# | 2 | Duplicate rows | exact duplicate rows | ~183 duplicate rows exist |
# | 3 | Missing / blank values | empty values per column | customer_id missing in 103 rows; category missing in 79 rows; all other columns complete |
# | 4 | Order statuses | distinct status values | completed 8,764 · refunded 403 · test 101 |
# | 5 | Categories | distinct category values | 6 categories present, plus 79 rows with no category |
# | 6 | Currencies & countries | distinct values | currencies: EUR (7,340), RON (1,928); countries: RO, DE, HU, BG |
# | 7 | Quantity | range & invalid values | ranges from -3 to 3; 167 rows are zero or negative |
# | 8 | Price | range & invalid values | ranges from 0 to 999,999; 24 rows priced 0; 13 rows priced 999,999 |
# | 9 | FX reference dates | range & validity | span 2026-08-23 → 2026-09-03; all valid dates |
# | 10 | Unique identifier | which column(s) uniquely identify a row | no single column is unique; the unique key is order_id + sku |
# 
# 
# **Profiling conclusions:**
# The dataset has 9,268 order-line rows. 
# 
# It contains duplicate rows, some missing values (customer_id, category), a non-real "test" status, out-of-range quantities and a placeholder
# price, and dates in the expected FX range. 
# 
# No single column is unique — rows are identified by
# order_id + sku. 


# MARKDOWN ********************

# ## 1. Size of the table
# How many rows and columns are we dealing with?

# CELL ********************

# MAGIC %%sql
# MAGIC -- Counts every row in the table so we know how much data we have
# MAGIC SELECT COUNT(*) AS total_rows FROM orders_raw

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 2. Are there duplicate rows?
# If total rows is higher than unique rows, some rows are exact copies.

# CELL ********************

# MAGIC %%sql
# MAGIC -- Compares total rows vs. rows that are truly unique.
# MAGIC -- COUNT(DISTINCT ...all columns...) counts each unique combination once,
# MAGIC -- so total minus unique = how many rows are exact copies.
# MAGIC SELECT
# MAGIC   COUNT(*) AS total_rows,
# MAGIC   COUNT(DISTINCT order_id, customer_id, customer_email, order_ts, status, channel,
# MAGIC                  sku, product_name, category, qty, unit_price, currency, country, fx_reference_date) AS unique_rows,
# MAGIC   COUNT(*) - COUNT(DISTINCT order_id, customer_id, customer_email, order_ts, status, channel,
# MAGIC                  sku, product_name, category, qty, unit_price, currency, country, fx_reference_date) AS duplicate_rows
# MAGIC FROM orders_raw

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 3. Missing or blank values (per column)
# Counts both truly empty (NULL) and blank text ("") for every column at once.

# CELL ********************

# MAGIC %%sql
# MAGIC -- For each column, adds 1 every time the value is empty (NULL) or blank ("").
# MAGIC -- SUM(CASE WHEN ... THEN 1 ELSE 0 END) is just "count the rows that match this condition".
# MAGIC SELECT
# MAGIC   SUM(CASE WHEN order_id          IS NULL OR TRIM(order_id)          = '' THEN 1 ELSE 0 END) AS null_order_id,
# MAGIC   SUM(CASE WHEN customer_id       IS NULL OR TRIM(customer_id)       = '' THEN 1 ELSE 0 END) AS null_customer_id,
# MAGIC   SUM(CASE WHEN customer_email    IS NULL OR TRIM(customer_email)    = '' THEN 1 ELSE 0 END) AS null_email,
# MAGIC   SUM(CASE WHEN order_ts          IS NULL OR TRIM(order_ts)          = '' THEN 1 ELSE 0 END) AS null_order_ts,
# MAGIC   SUM(CASE WHEN status            IS NULL OR TRIM(status)            = '' THEN 1 ELSE 0 END) AS null_status,
# MAGIC   SUM(CASE WHEN category          IS NULL OR TRIM(category)          = '' THEN 1 ELSE 0 END) AS null_category,
# MAGIC   SUM(CASE WHEN qty               IS NULL OR TRIM(qty)               = '' THEN 1 ELSE 0 END) AS null_qty,
# MAGIC   SUM(CASE WHEN unit_price        IS NULL OR TRIM(unit_price)        = '' THEN 1 ELSE 0 END) AS null_unit_price,
# MAGIC   SUM(CASE WHEN currency          IS NULL OR TRIM(currency)          = '' THEN 1 ELSE 0 END) AS null_currency,
# MAGIC   SUM(CASE WHEN country           IS NULL OR TRIM(country)           = '' THEN 1 ELSE 0 END) AS null_country,
# MAGIC   SUM(CASE WHEN fx_reference_date IS NULL OR TRIM(fx_reference_date) = '' THEN 1 ELSE 0 END) AS null_fx_date
# MAGIC FROM orders_raw

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 4.  What order statuses exist?

# CELL ********************

# MAGIC %%sql
# MAGIC -- Groups the rows by status and counts each one,
# MAGIC -- so we can spot statuses that aren't real sales (like 'test').
# MAGIC SELECT status, COUNT(*) AS how_many
# MAGIC FROM orders_raw
# MAGIC GROUP BY status
# MAGIC ORDER BY how_many DESC

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 5. What categories exist?

# CELL ********************

# MAGIC %%sql
# MAGIC -- Lists each category with its row count; a NULL group reveals the missing categories.
# MAGIC SELECT category, COUNT(*) AS how_many
# MAGIC FROM orders_raw
# MAGIC GROUP BY category
# MAGIC ORDER BY how_many DESC

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 6. Currencies and countries

# CELL ********************

# MAGIC %%sql
# MAGIC -- We need to know which currencies must be converted to EUR later.
# MAGIC -- Lists currencies and countries in one result.
# MAGIC -- UNION ALL just stacks the two lists on top of each other.
# MAGIC SELECT 'currency' AS field, currency AS value, COUNT(*) AS how_many FROM orders_raw GROUP BY currency
# MAGIC UNION ALL
# MAGIC SELECT 'country' AS field, country AS value, COUNT(*) AS how_many FROM orders_raw GROUP BY country
# MAGIC ORDER BY field, how_many DESC

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 7. Quantity checks

# CELL ********************

# MAGIC %%sql
# MAGIC -- Look for zero/negative quantities and any valu that isn't a whole number.
# MAGIC -- Checks quantities: smallest/largest value, how many are zero-or-negative,
# MAGIC -- and how many aren't a proper whole number. RLIKE tests the text against a number pattern.
# MAGIC SELECT
# MAGIC   MIN(CAST(qty AS INT)) AS min_qty,
# MAGIC   MAX(CAST(qty AS INT)) AS max_qty,
# MAGIC   SUM(CASE WHEN CAST(qty AS INT) <= 0 THEN 1 ELSE 0 END) AS zero_or_negative,
# MAGIC   SUM(CASE WHEN qty IS NULL OR qty NOT RLIKE '^-?[0-9]+$' THEN 1 ELSE 0 END) AS not_a_whole_number
# MAGIC FROM orders_raw

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 8. Price checks

# CELL ********************

# MAGIC %%sql
# MAGIC -- Look for zero prices, the fake 999999 placeholder, and any non-numeric price.
# MAGIC -- Checks prices: smallest/largest, how many are 0, how many are the fake 999999 placeholder,
# MAGIC -- and how many aren't a valid number at all.
# MAGIC SELECT
# MAGIC   MIN(CAST(unit_price AS DOUBLE)) AS min_price,
# MAGIC   MAX(CAST(unit_price AS DOUBLE)) AS max_price,
# MAGIC   SUM(CASE WHEN CAST(unit_price AS DOUBLE) = 0 THEN 1 ELSE 0 END) AS zero_price,
# MAGIC   SUM(CASE WHEN CAST(unit_price AS DOUBLE) = 999999 THEN 1 ELSE 0 END) AS placeholder_999999,
# MAGIC   SUM(CASE WHEN unit_price IS NULL OR unit_price NOT RLIKE '^[0-9]+([.][0-9]+)?$' THEN 1 ELSE 0 END) AS not_a_number
# MAGIC FROM orders_raw

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 9. FX reference dates

# CELL ********************

# MAGIC %%sql
# MAGIC -- These decide which exchange rate to use. Check the range and that all are valid dates.
# MAGIC -- Finds the earliest and latest FX reference date, and counts any that aren't valid dates.
# MAGIC -- TRY_CAST turns bad dates into NULL instead of erroring.
# MAGIC SELECT
# MAGIC   MIN(TRY_CAST(fx_reference_date AS DATE)) AS earliest_fx_date,
# MAGIC   MAX(TRY_CAST(fx_reference_date AS DATE)) AS latest_fx_date,
# MAGIC   SUM(CASE WHEN TRY_CAST(fx_reference_date AS DATE) IS NULL THEN 1 ELSE 0 END) AS invalid_dates
# MAGIC FROM orders_raw

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 10. What is the unique identifier?

# CELL ********************

# MAGIC %%sql
# MAGIC -- Find out if any single column can uniquely identify a row.
# MAGIC -- Count the total rows, then count the distinct (different) values in each column.
# MAGIC -- If a column's distinct count equals total_rows, that column is unique.
# MAGIC -- if all of them are smaller, then no single column is a unique identifier.
# MAGIC 
# MAGIC SELECT
# MAGIC   COUNT(*)                     AS total_rows,
# MAGIC   COUNT(DISTINCT order_id)     AS distinct_order_id,
# MAGIC   COUNT(DISTINCT sku)          AS distinct_sku,
# MAGIC   COUNT(DISTINCT customer_id)  AS distinct_customer_id,
# MAGIC   COUNT(DISTINCT customer_email) AS distinct_customer_email
# MAGIC FROM orders_raw

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }
