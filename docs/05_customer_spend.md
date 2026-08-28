# 5. Customer spend in EUR — customer_spend_eur

**Goal:** show the total amount each customer spent, in EUR.

**What happens:**
- Joins `orders_clean` to `fx_rates` on the order's `fx_reference_date` and currency.
- Converts each order to EUR: `line_total / rate`. EUR orders stay the same (rate = 1); RON orders are
  divided by the ~5.25 rate.
- Counts only **completed** orders (a refund isn't "spent").
- Sums the EUR amount per customer, highest first.

**Decision:** completed orders only. "Spent" means money that stayed spent — refunds return the money,
so they don't count.

**Result:** 1,866 customers, total ≈ €713,984.79.

**Conclusion:** every customer's spending is now in one currency (EUR), so RON and EUR customers can be
compared fairly, each order converted using the rate for its own reference date.
