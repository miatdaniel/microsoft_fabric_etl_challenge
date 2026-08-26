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

# ## Cleaning Summary — orders_raw → orders_clean
# 
# Approach: work on a copy (`orders_clean`); move every bad row to a quarantine table
# (`orders_quarantine`) with a reason, then remove it from the clean table. No values were
# recovered (fixing them is left for later). Nothing was lost: clean + quarantine = the original 9,268.
# 
# | Step | Finding | Decision | Action | Rows |
# |------|---------|----------|--------|------|
# | 1 | 183 exact duplicate rows | keep one copy, remove the rest | quarantined as 'duplicate row' | 183 |
# | 2 | 97 internal 'test' orders | not real sales | quarantined as 'test order' | 97 |
# | 3 | 77 rows with missing category | can't trust; recovery left for later | quarantined as 'missing category' | 77 |
# | 4 | 96 rows with missing customer id | can't attribute; recovery left for later | quarantined as 'missing customer id' | 96 |
# | 5 | 161 rows with zero/negative quantity | not a valid order | quarantined as 'invalid quantity' | 161 |
# | 6 | 13 rows priced 999999 | fake placeholder, not a real price | quarantined as 'placeholder price' | 13 |
# | — | 24 rows priced 0 | plausibly free/promo items | kept (no evidence they're wrong) | 0 |
# 
# **Result:** `orders_clean` = 8,641 rows · `orders_quarantine` = 627 rows · total = 9,268 (reconciles).
# 
# **Key decisions:**
# - Chose to quarantine, not delete — bad rows are preserved with a reason for later review.
# - Chose not to recover missing category/customer id at this stage (business needs to decide based on quarantine).
# - Kept zero-priced rows (only the obvious 999999 placeholder was removed).
# - The clean table still holds text columns; conversion to real numbers/dates happens in the
#   later steps that need them (EUR conversion and the revenue tables).
# 
# **Note on automation:** cleaning is a full refresh (rebuilds from raw each run) — safe and
# idempotent for this small, static dataset; at scale, incremental processing would be preferred.


# MARKDOWN ********************

# ## 1. Set up the working table and the quarantine table

# CELL ********************

# MAGIC %%sql
# MAGIC -- Makes a new table called orders_clean, filled with a full copy of the raw data.
# MAGIC -- We clean the copy so the original orders_raw stays safe and untouched.
# MAGIC -- It just confirms the table was created (it now holds all 9268 rows to start).
# MAGIC 
# MAGIC CREATE OR REPLACE TABLE orders_clean AS
# MAGIC SELECT * FROM orders_raw

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Creates an empty quarantine table with the same columns plus a "reject_reason" column.
# MAGIC -- This is where every bad row will be parked, tagged with the reason it was removed.
# MAGIC -- It confirms the table was created; it has 0 rows for now (WHERE 1 = 0 = no rows).
# MAGIC CREATE OR REPLACE TABLE orders_quarantine AS
# MAGIC SELECT *, CAST(NULL AS STRING) AS reject_reason
# MAGIC FROM orders_raw
# MAGIC WHERE 1 = 0

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 2. Remove duplicate rows

# CELL ********************

# MAGIC %%sql
# MAGIC -- Builds a helper TABLE that numbers each copy of a row (1 = keep, 2+ = duplicate).
# MAGIC -- A real TABLE (not a view) so the next step can rebuild orders_clean without a self-reference.
# MAGIC CREATE OR REPLACE TABLE orders_ranked AS
# MAGIC SELECT *,
# MAGIC   ROW_NUMBER() OVER (
# MAGIC     PARTITION BY order_id, customer_id, customer_email, order_ts, status, channel, sku,
# MAGIC                  product_name, category, qty, unit_price, currency, country, fx_reference_date
# MAGIC     ORDER BY order_id
# MAGIC   ) AS copy_number
# MAGIC FROM orders_clean

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Moves the extra copies (copy_number > 1) to quarantine, tagged 'duplicate row'.
# MAGIC INSERT INTO orders_quarantine
# MAGIC SELECT order_id, customer_id, customer_email, order_ts, status, channel, sku, product_name,
# MAGIC        category, qty, unit_price, currency, country, fx_reference_date, 'duplicate row'
# MAGIC FROM orders_ranked
# MAGIC WHERE copy_number > 1

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Rebuilds orders_clean from the helper TABLE, keeping only the first copy of each row.
# MAGIC -- Reading from orders_ranked (a separate table) avoids the self-reference problem.
# MAGIC CREATE OR REPLACE TABLE orders_clean AS
# MAGIC SELECT order_id, customer_id, customer_email, order_ts, status, channel, sku, product_name,
# MAGIC        category, qty, unit_price, currency, country, fx_reference_date
# MAGIC FROM orders_ranked
# MAGIC WHERE copy_number = 1

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Quarantined = 183, remaining = 9085.
# MAGIC SELECT 'quarantined (duplicate row)' AS bucket, COUNT(*) AS rows
# MAGIC FROM orders_quarantine WHERE reject_reason = 'duplicate row'
# MAGIC UNION ALL
# MAGIC SELECT 'remaining in orders_clean', COUNT(*) FROM orders_clean

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 3. Remove test orders

# CELL ********************

# MAGIC %%sql
# MAGIC -- Moves 'test' status orders to quarantine, tagged 'test order'.
# MAGIC -- They are internal tests, not real sales.
# MAGIC INSERT INTO orders_quarantine
# MAGIC SELECT *, 'test order' FROM orders_clean WHERE status = 'test'

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Removes those test orders from the clean table.
# MAGIC DELETE FROM orders_clean WHERE status = 'test'

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Shows what this step quarantined vs what remains in the clean table.
# MAGIC SELECT 'quarantined (test order)' AS bucket, COUNT(*) AS rows
# MAGIC FROM orders_quarantine WHERE reject_reason = 'test order'
# MAGIC UNION ALL
# MAGIC SELECT 'remaining in orders_clean', COUNT(*) FROM orders_clean

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 4. Remove rows with missing category

# CELL ********************

# MAGIC %%sql
# MAGIC -- Moves rows with no category to quarantine, tagged 'missing category'.
# MAGIC -- We can't trust a row with no category; fixing it is left for later.
# MAGIC INSERT INTO orders_quarantine
# MAGIC SELECT *, 'missing category' FROM orders_clean WHERE category IS NULL OR TRIM(category) = ''

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Removes those missing-category rows from the clean table.
# MAGIC DELETE FROM orders_clean WHERE category IS NULL OR TRIM(category) = ''

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Shows what this step quarantined vs what remains.
# MAGIC SELECT 'quarantined (missing category)' AS bucket, COUNT(*) AS rows
# MAGIC FROM orders_quarantine WHERE reject_reason = 'missing category'
# MAGIC UNION ALL
# MAGIC SELECT 'remaining in orders_clean', COUNT(*) FROM orders_clean

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 5. Remove rows with missing customer id

# CELL ********************

# MAGIC %%sql
# MAGIC -- Moves rows with no customer id to quarantine, tagged 'missing customer id'.
# MAGIC -- We can't attribute the order to a customer; fixing it is left for later..
# MAGIC INSERT INTO orders_quarantine
# MAGIC SELECT *, 'missing customer id' FROM orders_clean WHERE customer_id IS NULL OR TRIM(customer_id) = ''

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC --Removes those missing-customer-id rows from the clean table.
# MAGIC DELETE FROM orders_clean WHERE customer_id IS NULL OR TRIM(customer_id) = ''

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Shows what this step quarantined vs what remains.
# MAGIC SELECT 'quarantined (missing customer id)' AS bucket, COUNT(*) AS rows
# MAGIC FROM orders_quarantine WHERE reject_reason = 'missing customer id'
# MAGIC UNION ALL
# MAGIC SELECT 'remaining in orders_clean', COUNT(*) FROM orders_clean

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 6. Remove invalid quantities

# CELL ********************

# MAGIC %%sql
# MAGIC -- Moves rows where quantity is 0 or negative to quarantine, tagged 'invalid quantity'.
# MAGIC -- An order can't have zero or negative items. TRY_CAST safely turns the text into a number.
# MAGIC INSERT INTO orders_quarantine
# MAGIC SELECT *, 'invalid quantity' FROM orders_clean WHERE TRY_CAST(qty AS INT) <= 0

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Removes those invalid-quantity rows from the clean table.
# MAGIC DELETE FROM orders_clean WHERE TRY_CAST(qty AS INT) <= 0

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Shows what this step quarantined vs what remains.
# MAGIC SELECT 'quarantined (invalid quantity)' AS bucket, COUNT(*) AS rows
# MAGIC FROM orders_quarantine WHERE reject_reason = 'invalid quantity'
# MAGIC UNION ALL
# MAGIC SELECT 'remaining in orders_clean', COUNT(*) FROM orders_clean

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 7. Remove placeholder prices

# CELL ********************

# MAGIC %%sql
# MAGIC -- Moves rows priced exactly 999999 to quarantine, tagged 'placeholder price'.
# MAGIC -- 999999 is a fake stand-in value, not a real price.
# MAGIC INSERT INTO orders_quarantine
# MAGIC SELECT *, 'placeholder price' FROM orders_clean WHERE TRY_CAST(unit_price AS DOUBLE) = 999999

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Removes those placeholder-price rows from the clean table.
# MAGIC DELETE FROM orders_clean WHERE TRY_CAST(unit_price AS DOUBLE) = 999999

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Shows what this step quarantined vs what remains.
# MAGIC SELECT 'quarantined (placeholder price)' AS bucket, COUNT(*) AS rows
# MAGIC FROM orders_quarantine WHERE reject_reason = 'placeholder price'
# MAGIC UNION ALL
# MAGIC SELECT 'remaining in orders_clean', COUNT(*) FROM orders_clean

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 8. Verify — nothing lost / reconcile totals

# CELL ********************

# MAGIC %%sql
# MAGIC -- Clean + quarantine must equal the original 9268 rows.
# MAGIC -- Two rows — clean and quarantine; they should sum to 9268.
# MAGIC SELECT 'clean' AS bucket, COUNT(*) AS rows FROM orders_clean
# MAGIC UNION ALL
# MAGIC SELECT 'quarantine', COUNT(*) FROM orders_quarantine

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Full breakdown of why rows were quarantined.
# MAGIC -- duplicate row 183 · invalid quantity 161 · test order 97 · missing customer id 96 · missing category 77 · placeholder price 13 (= 627)- from above
# MAGIC 
# MAGIC SELECT reject_reason, COUNT(*) AS how_many
# MAGIC FROM orders_quarantine
# MAGIC GROUP BY reject_reason
# MAGIC ORDER BY how_many DESC

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 9. Convert columns to proper types
# 
# The clean table currently holds everything as text. Here we give each column its correct type,
# based on what it contains and how it's used (do we do math on it? is it a date?).
# 
# | Column | Type | Why |
# |--------|------|-----|
# | order_id | text | an identifier/label — never used for math |
# | customer_id | whole number | numeric id used to group orders per customer |
# | customer_email | text | it's text |
# | order_ts | timestamp | a point in time (arrives in 3 formats, standardised here) |
# | status | text | a label |
# | channel | text | a label |
# | sku | text | a product code — a label, not math |
# | product_name | text | text |
# | category | text | a label |
# | qty | whole number | you count items; used in math (qty × price) |
# | unit_price | decimal | money has decimals; used in math |
# | line_total | decimal | qty × unit_price (money) |
# | currency | text | a code |
# | country | text | a code |
# | fx_reference_date | date | a calendar date; used to join exchange rates |
# 
# Note: ids/codes like order_id and sku stay text on purpose — "looks like a number" is not the
# same as "used for math". We build a typed copy first, then swap it in, to avoid reading and
# overwriting the same table at once.


# CELL ********************

# MAGIC %%sql
# MAGIC -- Builds a typed copy of orders_clean (numbers, dates) into a temporary table.
# MAGIC -- A clean table should have real types; building into a separate table avoids the
# MAGIC --       "read and overwrite the same table" problem we hit earlier.
# MAGIC CREATE OR REPLACE TABLE orders_clean_typed AS
# MAGIC SELECT
# MAGIC   order_id,
# MAGIC   CAST(customer_id AS BIGINT)                       AS customer_id,
# MAGIC   customer_email,
# MAGIC   CASE
# MAGIC     WHEN order_ts RLIKE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$' THEN to_timestamp(order_ts, "yyyy-MM-dd'T'HH:mm:ss")
# MAGIC     WHEN order_ts RLIKE '^[0-9]{9,10}$'                                            THEN timestamp_seconds(CAST(order_ts AS BIGINT))
# MAGIC     WHEN order_ts RLIKE '^[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2}$'           THEN to_timestamp(order_ts, 'dd/MM/yyyy HH:mm')
# MAGIC   END                                               AS order_ts,
# MAGIC   status,
# MAGIC   channel,
# MAGIC   sku,
# MAGIC   product_name,
# MAGIC   category,
# MAGIC   CAST(qty AS INT)                                  AS qty,
# MAGIC   CAST(unit_price AS DOUBLE)                         AS unit_price,
# MAGIC   ROUND(CAST(qty AS INT) * CAST(unit_price AS DOUBLE), 2) AS line_total,
# MAGIC   currency,
# MAGIC   country,
# MAGIC   CAST(fx_reference_date AS DATE)                    AS fx_reference_date
# MAGIC FROM orders_clean

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Replaces orders_clean with the typed copy.
# MAGIC -- Reads from orders_clean_typed (a different table) so there's no self-reference.
# MAGIC CREATE OR REPLACE TABLE orders_clean AS
# MAGIC SELECT * FROM orders_clean_typed

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Removes the temporary typed table, no longer needed.
# MAGIC DROP TABLE IF EXISTS orders_clean_typed

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Shows the column types of orders_clean.
# MAGIC -- qty=int, unit_price/line_total=double, order_ts=timestamp, fx_reference_date=date.
# MAGIC DESCRIBE orders_clean

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Confirms the row count didn't change.
# MAGIC SELECT COUNT(*) AS rows FROM orders_clean

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }
