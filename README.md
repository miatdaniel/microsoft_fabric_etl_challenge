# Aqurate — Junior Data Engineer Challenge

An end-to-end ETL pipeline built on **Microsoft Fabric**: pull orders from an API, clean them, pull daily FX rates, convert to EUR, and produce two reporting tables — refreshed daily.

## What it does
1. **Ingest** orders from the API into `orders_raw`.
2. **Clean** them into `orders_clean` (bad rows moved to `orders_quarantine` with a reason).
3. **Pull** daily EUR↔RON exchange rates into `fx_rates`.
4. **Customer spend in EUR** → `customer_spend_eur`.
5. **Country/category revenue** (Books + Electronics, > €40,000) → `country_category_revenue`.
6. **Automate** — a daily pipeline refreshes the tables and posts a data-quality report to Teams.

## Architecture
- **Storage:** one Fabric Lakehouse (`lh_orders`) holding all tables.
- **Transforms:** Spark SQL in notebooks (cleaning + maths); Python only for the two API pulls.
- **Orchestration:** a Fabric Data Pipeline (`pipeline_daily_refresh`) on a daily schedule.

## Repo structure
| Folder | Contents |
|---|---|
| `fabric/` | the Fabric items — notebooks, the lakehouse, and the pipeline |
| `docs/` | short plain-language summary of each step |
| `results/` | CSV exports of the output tables |
| `screenshots/` | pipeline run, Teams report, daily schedule |

## Results
- **orders_raw** 9,268 → **orders_clean** 8,641 + **orders_quarantine** 627
- **customer_spend_eur** — 1,866 customers, ≈ €713,984.79
- **country_category_revenue** — RO €146,608.56, HU €40,823.50

## More detail
- **[WRITEUP.md](WRITEUP.md)** — data issues & how handled, production monitoring, AI usage.
- **[PROJECT_STORY.md](PROJECT_STORY.md)** — the full step-by-step story, decisions, and issues.
- **[docs/](docs/)** — one short summary per step.

*Built with the help of GitHub Copilot; all decisions reviewed and verified.*
