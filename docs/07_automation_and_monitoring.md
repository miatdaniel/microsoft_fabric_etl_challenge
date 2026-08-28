# 7. Automation & monitoring

**Goal:** refresh the two final tables every day, and know immediately if something goes wrong.

## The daily pipeline
A Fabric Data Pipeline (`pipeline_daily_refresh`) runs these in order, each only if the previous one
succeeds:

```
run_fx_rates → run_customer_spend → run_country_revenue → run_data_quality_check → send report (Teams)
```

- Ingestion and cleaning are **not** in the daily run — `orders_raw` is static, so they only need to
  run once. The daily change comes from the exchange rates flowing into the two tables.
- `run_fx_rates` has a **retry** (2 attempts, 90s apart) because it calls the internet.
- Every run rebuilds its table from scratch (full refresh), so re-running never creates duplicates —
  the pipeline is safe to run over and over.

## Monitoring
- **Failure alerts:** every step has a Teams "on-failure" message, so if a step fails I get notified
  (and the later steps are skipped, not run on bad data).
- **Monitor tab:** Fabric's run history shows every run's status.
- **Data-quality check:** the last step checks the actual data — most importantly that every order has
  a matching exchange rate (so nothing is silently dropped), plus no negative totals and sane row
  counts. It posts a **daily report to Teams** with the numbers.

## Catching a silent failure
A job can "succeed" but still be wrong, or not run at all. That's covered by: the daily data-quality
report arriving (if it's missing or the numbers look off, that's the signal), the failure alerts, and
— at larger scale — a dead-man's-switch that alerts if no successful run happens within 24 hours.

## Honest note
Email alerts (Outlook) didn't work because the account's mailbox is on-premises, which the connector
can't reach (`MailboxNotEnabledForRESTAPI`). I switched to **Teams**, which works, and tested it by
forcing a step to fail and confirming the alert arrived.

## Scaling
Full refresh is the right choice for this small, static dataset (runs in seconds). At real scale I'd
switch to incremental processing (only handle new/changed rows) so the daily job stays fast.

## Teardown
The schedule can be paused or deleted after a few days — the data is static, so there's no need to
keep it running.
