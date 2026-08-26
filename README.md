# Aqurate — Junior Data Engineer Challenge

An end-to-end ETL pipeline built on **Microsoft Fabric**: pull orders from an API, clean them,
pull daily FX rates, convert to EUR, and produce two reporting tables — refreshed daily.

## Architecture

```
Orders API ─▶ orders_raw ─▶ (clean + quarantine) ─▶ orders_clean ─┐
FX API (frankfurter.dev) ─────────────────────────▶ fx_rates ─────┤
                                                                  ├─▶ customer_spend_eur
                                                                  └─▶ country_category_revenue
A daily Data Pipeline runs the FX pull + the two tables + a data-quality check, with Teams alerts.
```

- **Storage:** one Fabric **Lakehouse** (`lh_orders`) holding all tables.
- **Transforms:** Spark SQL in notebooks (cleaning + aggregation); a little Python only for the two API pulls.
- **Orchestration:** a Fabric **Data Pipeline** (`pipeline_daily_refresh`) on a daily schedule.

## Tables produced
| Table | What it is |
|---|---|
| `orders_raw` | raw orders pulled from the API (9,268 rows) |
| `orders_clean` | cleaned orders (8,641 rows) |
| `orders_quarantine` | bad rows removed during cleaning, with a reason (627 rows) |
| `fx_rates` | daily EUR↔RON exchange rates |
| `customer_spend_eur` | total EUR spend per customer (1,866 customers) |
| `country_category_revenue` | Books+Electronics revenue by country, > €40,000 (RO, HU) |

## Notebooks (in `fabric/`)
1. `notebook_ingest_orders_raw` — pull `orders_raw` from the API (Python, paginated).
2. `notebook_orders_raw_profiling` — data profiling (read-only; run once).
3. `notebook_clean_orders` — clean + quarantine + type conversion → `orders_clean`.
4. `notebook_fx_rates` — pull EUR↔RON rates from frankfurter.dev → `fx_rates`.
5. `notebook_customer_spend` — `customer_spend_eur`.
6. `notebook_country_revenue` — `country_category_revenue`.
7. `data_check_after_pipeline_run` — data-quality checks + report.

## Automation
`pipeline_daily_refresh` runs daily:
`fx_rates → customer_spend → country_revenue → data_quality_check → Teams report`,
with a Teams failure alert on every step. (Ingest + cleaning run once — `orders_raw` is static.)

## Results (latest run)
- **customer_spend_eur:** 1,866 customers, ≈ **€713,984.79** total (completed orders only).
- **country_category_revenue:** **RO €146,608.56**, **HU €40,823.50** (DE and BG fall below the €40k threshold).

See `WRITEUP.md` for data issues, decisions, monitoring, and AI usage.
See `results/` for CSV exports and `screenshots/` for pipeline + schedule proof.
