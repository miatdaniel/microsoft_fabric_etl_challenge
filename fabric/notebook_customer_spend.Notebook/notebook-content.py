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

# ## Customer Spend Summary — customer_spend_eur
# 
# Purpose: calculate the total amount each customer spent, expressed in EUR.
# 
# | Step | What it does | Result |
# |------|--------------|--------|
# | 1 | Join clean orders to the exchange rates on the order's fx_reference_date and currency | rates matched to each order |
# | 2 | Convert each line to EUR (line_total ÷ rate; EUR stays as-is, RON divided by ~5.25) | amounts in EUR |
# | 3 | Keep only completed orders (refunds are not "spent") | refunded orders excluded |
# | 4 | Sum the EUR amounts per customer, ranked highest first | one row per customer |
# 
# **Decision:** only `completed` orders count as spend — a refund returns the money, so it isn't
# "spent." (Including refunds would give 1,880 customers / €749,116.15; we did not use that.)
# 
# **Result:** 1,866 customers · total spend €713,984.79.
# 
# ### Conclusion
# Every customer's spending is now shown in a single currency (EUR), so customers paying in RON
# and EUR can be compared fairly. Each order was converted using the exchange rate for its own
# reference date, and only real (completed) sales were counted. The result is a clean, ranked list
# of how much each customer actually spent.


# CELL ********************

# MAGIC %%sql
# MAGIC -- Sums each customer's spend, converting RON orders to EUR using the exchange rate for that order's fx_reference_date. 
# MAGIC -- Only completed orders count as spend (refunds are excluded).
# MAGIC -- Total amount each customer spent, converted to EUR.
# MAGIC -- The project asks for spend per customer in EUR; RON orders are converted using the
# MAGIC --       exchange rate for that order's fx_reference_date.
# MAGIC -- Line_total / rate_to_eur  ->  RON amount / (RON per 1 EUR) = EUR amount.
# MAGIC --      For EUR orders the rate is 1.0, so the amount stays the same.
# MAGIC -- One row per customer with their total EUR spend, highest first.
# MAGIC CREATE OR REPLACE TABLE customer_spend_eur AS
# MAGIC SELECT
# MAGIC   o.customer_id,
# MAGIC   ROUND(SUM(o.line_total / f.rate_to_eur), 2) AS total_spend_eur
# MAGIC FROM orders_clean o
# MAGIC JOIN fx_rates f
# MAGIC   ON  f.fx_date  = o.fx_reference_date
# MAGIC   AND f.currency = o.currency
# MAGIC WHERE o.status = 'completed'          -- count only completed orders (refunds are not "spent")
# MAGIC GROUP BY o.customer_id
# MAGIC ORDER BY total_spend_eur DESC

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Number of customers and total EUR across everyone.
# MAGIC SELECT COUNT(*) AS customers, ROUND(SUM(total_spend_eur), 2) AS grand_total_eur
# MAGIC FROM customer_spend_eur

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }
