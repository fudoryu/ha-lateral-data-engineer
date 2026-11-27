# ha-lateral-data-engineer

## Production design note

### Monitoring, alerting and data-quality failures

The pipeline already produces the signals; production adds collection, storage and alerting on top.

**Today, locally**
- Every step logs structured events (ADR-0024): requests with duration, retries with their reason, refetched pages, unknown API fields, skipped runs, load and publish. `--log-format json` gives one JSON object per line.
- dbt tests run on every build, before publish: a failing test stops the chain and the previous warehouse stays live (write-audit-publish, ADR-0007).
- Each run's manifest records its warnings, configuration and code version; every value carries `run_id` and `source_response_id` back to the exact landed page.

**In production**
- **Logs:** JSON logs from each task go to CloudWatch Logs (or Datadog). Every event carries `run_id`, so one query reconstructs a run end to end.
- **Metrics,** derived from the logs or emitted by the tasks: requests, retries and request latency per run; rows per indicator; extract and build duration; **freshness**, as the time since the last committed run and the source's `lastupdated` per indicator.
- **Data quality:** dbt test results (`run_results.json`) are stored per build, so failures and warnings can be trended. Volume and coverage are compared with the previous run: row counts per indicator, `missing_row` and `null_value` counts, and the revision rate from the value-versions fact. Unknown-field warnings track schema drift in the API.
- **Lineage:** `source_response_id` points at the exact S3 object a value came from; dbt docs provide the model lineage graph.
- **Alerting:**

  | Severity | When |
  |---|---|
  | Page | extract failed after its retries; a dbt test failed, so publish was refused; no committed run within the freshness SLA (for example 26 hours for a daily schedule) |
  | Warn | retries above a threshold; new API fields; a spike in revisions; a drop in coverage between runs |

- **Investigating a failure:** nothing is lost on failure. Landed runs are immutable and the failed `.next` build is kept, so the same state can be rebuilt anywhere with `worldbank load --as-of <run_id>` and `dbt build`.
