# Tables — what each one contains

All tables live in the Fabric Lakehouse `lh_orders`.

## orders_raw
The orders pulled straight from the API, stored as-is (all columns are text at this stage).

| Column | Meaning |
|---|---|
| order_id | the order's id (repeats — an order can have several product lines) |
| customer_id | the customer who placed the order |
| customer_email | the customer's email |
| order_ts | when the order was placed (arrives in 3 different formats) |
| status | completed / refunded / test |
| channel | where the order came from (web, mobile_app, marketplace) |
| sku | the product code |
| product_name | the product's name |
| category | product category (Books, Electronics, …) |
| qty | quantity ordered |
| unit_price | price per item |
| currency | EUR or RON |
| country | country code (RO, DE, HU, BG) |
| fx_reference_date | the date to use for the exchange rate |

## orders_clean
The cleaned, properly-typed version of `orders_raw` — duplicates, test orders, and invalid rows
removed; types fixed; dates standardised. Same columns as `orders_raw`, **plus**:

| Column | Meaning |
|---|---|
| line_total | qty × unit_price (the line's total value) |

(Types are proper here: `customer_id` is a number, `order_ts` a timestamp, `qty` a whole number,
`unit_price`/`line_total` decimals, `fx_reference_date` a date.)

## orders_quarantine
The rows removed during cleaning, kept for review. Same columns as `orders_raw`, **plus**:

| Column | Meaning |
|---|---|
| reject_reason | why the row was removed (e.g. 'duplicate row', 'test order', 'invalid quantity') |

## fx_rates
The daily exchange rates used to convert to EUR.

| Column | Meaning |
|---|---|
| fx_date | the date the rate applies to |
| currency | EUR or RON |
| rate_to_eur | how many of this currency equal 1 EUR (EUR = 1.0) |

## customer_spend_eur
Total amount each customer spent, in EUR (completed orders only).

| Column | Meaning |
|---|---|
| customer_id | the customer |
| total_spend_eur | their total spend in EUR |

## country_category_revenue
Books + Electronics revenue by country, only countries above €40,000, ranked.

| Column | Meaning |
|---|---|
| country | country code |
| revenue_eur | total EUR revenue for Books + Electronics |
