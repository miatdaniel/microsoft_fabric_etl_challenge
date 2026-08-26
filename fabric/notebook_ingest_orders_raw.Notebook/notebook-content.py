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

# ## Ingestion Summary — orders_raw
# 
# Purpose: pull the raw orders from the source API and land them in the Lakehouse, unchanged.
# 
# | # | Step | What it does | Result |
# |---|------|--------------|--------|
# | 1 | Call the API | Requests the orders from the source endpoint, sending the required apikey | Connects to the source |
# | 2 | Page through all rows | The API returns max 1000 rows per call, so a loop keeps requesting the next 1000 until a short page signals the end | All pages collected |
# | 3 | Store values as text | Every value is converted to text so mixed whole-number/decimal columns don't clash on load (types are applied later, in cleaning) | Consistent, load-safe data |
# | 4 | Save to Lakehouse | Writes the collected rows into the `orders_raw` table (overwrite, so re-running is safe) | `orders_raw` created |
# | 5 | Verify row count | Counts rows in `orders_raw` and compares to the source total | 9,268 rows (matches source) |
# | 6 | Preview data | Selects the first 500 rows to eyeball the loaded data | Data looks correct |
# 
# **Ingestion conclusion:**
# All 9,268 order-line rows were pulled from the source API (with pagination) and stored as-is
# in the `orders_raw` Lakehouse table. Values are kept as text at this raw stage to avoid type
# conflicts; conversion to proper numbers/dates happens later. Row count matches the source,
# confirming nothing was lost or duplicated during ingestion.
# 
# **Source:** https://jzozteoirwfczccltcdr.supabase.co/rest/v1/orders_raw


# MARKDOWN ********************

# ## Step 1 — Ingest orders from the API
# 
# **What:** Pulls all the orders from the online API and saves them into a table called `orders_raw`.
# 
# **Why:** We need the raw data inside our Lakehouse before we can clean or analyse it. The API only sends 1000 rows at a time, so we loop until we've collected all of them. We store every value as text at this stage so mixed number/decimal columns don't cause errors — we turn them into proper numbers later, during cleaning.

# CELL ********************

import requests  # tool that lets us call the API over the internet

url = "https://jzozteoirwfczccltcdr.supabase.co/rest/v1/orders_raw"  # web address of the orders data
headers = {"apikey": "sb_publishable_Xwjiw--qkKcbMuSbKd6I2w_wN9mpNTv"}  # the key the API requires to let us in

rows = []   # empty list to collect all the orders
start = 0   # counter for which row we've reached; begin at 0
while True:                                          # keep looping until we tell it to stop
    headers["Range"] = f"{start}-{start+999}"        # ask for a chunk of 1000 rows
    batch = requests.get(url, headers=headers).json()  # call the API and read the result
    rows += batch                                    # add that chunk to our list
    if len(batch) < 1000:                            # fewer than 1000 means last page
        break                                        # stop the loop
    start += 1000                                    # otherwise move to the next chunk

print("Fetched", len(rows), "rows")   # should be 9268

# Convert every value to text so mixed whole-number/decimal columns don't clash.
# (We turn them back into real numbers later, in the cleaning step.)
text_rows = []                         # will hold the same rows, all values as text
for row in rows:                       # go through each order
    new_row = {}                       # a fresh copy of this order
    for key in row:                    # go through each field in the order
        value = row[key]               # the field's value
        if value is None:              # if it's empty
            new_row[key] = None        # keep it empty
        else:                          # otherwise
            new_row[key] = str(value)  # store it as text
    text_rows.append(new_row)          # add the fixed row to our list

df = spark.createDataFrame(text_rows)                   # turn the rows into a Spark table
df.write.mode("overwrite").saveAsTable("orders_raw")    # save into the Lakehouse as orders_raw
print("Saved orders_raw")                               # confirm it saved

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Check: did all the orders load?
# 
# **What:** Counts the rows in `orders_raw`.
# 
# **Why:** To confirm the ingest worked. We expect **9268** rows based on API https://jzozteoirwfczccltcdr.supabase.co/rest/v1/orders_raw — if the number matches, we know nothing was lost or duplicated before we move on.

# CELL ********************

# MAGIC %%sql
# MAGIC SELECT COUNT(*) AS row_count FROM orders_raw

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC select* from orders_raw
# MAGIC limit 500

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }
