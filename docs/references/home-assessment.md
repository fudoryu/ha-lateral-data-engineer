# Senior Challenge – Take Home Assessment

> Verbatim transcription of [`home-assessment.pdf`](home-assessment.pdf).
> This file is the immutable source. Do not edit it; the derived document is [`../requirements.md`](../requirements.md).

You are encouraged to use AI tools while working on this challenge.

## Scenario

A research team needs a dependable, traceable yearly dataset of country indicators from the World Bank API that analysts can query without knowing the API or working around missing data.

Use only the public API (no account or key needed) as the production data source [World Bank API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures)

**Countries:** BRA, CAN, DEU, GBR, IND, JPN, MEX, USA, ZAF

| Indicator | Code |
|---|---|
| Population, total | `SP.POP.TOTL` |
| GDP, current US dollars | `NY.GDP.MKTP.CD` |
| GDP per capita, current US dollars | `NY.GDP.PCAP.CD` |
| Life expectancy at birth, total years | `SP.DYN.LE00.IN` |

**Years:** 2018 through 2024. Some values may not be available. Treat missing data as a meaningful outcome, not as zero.

## Task

Build a local, configuration-driven pipeline that retrieves this data, prepares it for analytics, and produces a small set of reporting outputs.

## Requirements

### 1. Data ingestion

- Retrieve country metadata and the required indicator observations from the API.
- Handle paging and API failures.
- Make every output value traceable to the API response it came from.
- Provide a single documented command that runs the pipeline locally from a clean checkout.
- A re-run with unchanged source data must not create duplicate analytical records.
- Do not create cloud resources, paid accounts, or API accounts.

### 2. Data model and transformations

- Keep the raw source representation separate from cleaned and analytics-ready data.
- Design and document the grain, business keys, and relationships of the final data model.
- Standardize the data so analysts don't need to understand the source format.
- Make it possible to add a country or indicator through configuration or documented parameters without copying pipeline code.

### 3. Analytics outputs

Provide SQL queries, views, tables, or an equivalent reproducible reporting layer that answers:

- Which country-indicator-year combinations are missing or incomplete?
- What is the year-over-year change for each available indicator, handling missing or zero prior values?
- How do the selected countries compare for the latest available year of each indicator?
- How do the indicators compare across income groups, by year?

Optional: an extra view, dashboard, or Power BI report. Not required.

### 4. Data quality and testing

- Implement automated data-quality checks and tests that give you confidence in correctness and safe reprocessing.
- Check that related indicators are consistent with each other.
- Tests must run without calling the live API.

### 5. Production design note

Add a short section to the README (about one page; bullet points are fine) describing how you would operate this in production. Address:

- Scheduling and incremental refreshes
- Handling late, corrected, or changed source data
- Monitoring, alerting, and data-quality failures
- Backfills and replay-ability
- How the local design would map to Snowflake plus AWS Glue or EMR, or to comparable Azure services

### 6. Deliverable

- Any language or stack; it must run locally by following the README (Docker is fine).
- README with setup instructions, assumptions, trade-offs, a short walkthrough of your key decisions, and AI usage.
- Sample output of the reporting queries (for example, CSV).
- Git/GitHub repository (with commit history) containing all the above.

## Notes

- This assignment is intentionally open-ended. Focus on correctness, structure, and clarity. Correct, idempotent ingestion and a clear data model matter the most.
- Suggested time limit: 4 to 6 hours. Stop when you reach it and document unfinished work and next steps in the README. If time runs short, work in this order:
  1. Correct, idempotent ingestion and a clearly defined data model
  2. Data-quality checks and tests
  3. The required analytics outputs
  4. README, production design note, and walkthrough
  5. Anything optional (extra views, dashboards)
