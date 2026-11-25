# Requirements: World Bank Country Indicators Dataset

| | |
|---|---|
| **Source** | [`references/home-assessment.md`](references/home-assessment.md) (transcribed from the assessment PDF) |
| **Status** | Draft |
| **Scope of this document** | *What* and *why* only. |

## 1. Problem

A research team needs a **dependable, traceable yearly dataset** of country indicators from the World Bank API. Analysts must be able to query it **without knowing the API** and **without working around missing data**.

## 2. Users

| User | Need |
|---|---|
| Research analyst | Query clean, standardized yearly indicators with SQL; see clearly where data is missing. |
| Data engineer / maintainer | Run, re-run, and extend the pipeline safely; trace any value back to its source. |

## 3. Goals

- G1: A correct, reproducible yearly dataset for the configured scope (FR-ING-\*, FR-MOD-\*, NFR-6).
- G2: Data analysts can trust: traceable, idempotent, honest about missing values (NFR-1 to NFR-3).
- G3: Reporting outputs that answer the four analytics questions (§5.3).
- G4: Scope that grows through configuration alone (NFR-4).

## 4. Scope

**Source:** the World Bank public API only ([API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures)).

**Countries (initial)**

| ISO3 | Country |
|---|---|
| BRA | Brazil |
| CAN | Canada |
| DEU | Germany |
| GBR | United Kingdom |
| IND | India |
| JPN | Japan |
| MEX | Mexico |
| USA | United States |
| ZAF | South Africa |

**Indicators (initial)**

| Code | Name |
|---|---|
| `SP.POP.TOTL` | Population, total |
| `NY.GDP.MKTP.CD` | GDP, current US dollars |
| `NY.GDP.PCAP.CD` | GDP per capita, current US dollars |
| `SP.DYN.LE00.IN` | Life expectancy at birth, total years |

**Years:** 2018 through 2024, inclusive.

## 5. Functional requirements

### 5.1 Ingestion

| ID       | Requirement                                                                                   | Acceptance criteria                                                                                                           |
| -------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| FR-ING-1 | Retrieve **country metadata** from the API.                                                   | Metadata for every configured country is stored.                                                                              |
| FR-ING-2 | Retrieve **indicator observations** for the configured scope.                                 | Observations exist for every configured country × indicator, for the configured years.                                        |
| FR-ING-3 | Handle **paging**.                                                                            | All pages are retrieved; the row count matches what the API reports. Proven with a small page size in tests.                  |
| FR-ING-4 | Handle **API failures**.                                                                      | Transient failures are retried; persistent failures produce a clear error and never produce partial or wrong analytical data. |

### 5.2 Data model and transformations

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-MOD-1 | Keep the **raw source representation separate** from cleaned and analytics-ready data. | Distinct layers exist; raw holds the source as received. |
| FR-MOD-2 | **Design and document** the grain, business keys, and relationships of the final data model. | Docs state the grain, keys, and relationships of each final table. |
| FR-MOD-3 | **Standardize** the data so analysts don't need to understand the source format. | Final tables use typed, consistently named columns, with no nested or source-specific structures. |

### 5.3 Analytics outputs

A reproducible reporting layer (SQL queries, views, tables, or equivalent) that answers:

| ID | Question | Acceptance criteria |
|---|---|---|
| FR-ANA-1 | Which country-indicator-year combinations are **missing or incomplete**? | Every expected combination is listed with its status. |
| FR-ANA-2 | What is the **year-over-year change** for each available indicator, handling **missing or zero prior values**? | Missing or zero prior values give a defined, explained result instead of an error or a misleading number. |
| FR-ANA-3 | How do the selected countries compare for the **latest available year** of each indicator? | For each indicator, the countries are compared at the latest available year, and the year used is shown with each value. The definition of "latest available" is documented (Q2). |
| FR-ANA-4 | How do the indicators compare **across income groups, by year**? | Each income group × indicator × year has comparable values, and the aggregation method is documented (Q4). |
| FR-ANA-5 *(optional)* | An extra view, dashboard, or Power BI report. | n/a |

### 5.4 Data quality and testing

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-DQ-1 | **Automated** data-quality checks and tests that give confidence in **correctness and safe reprocessing**. | Checks run on every pipeline run; tests run with one command. |
| FR-DQ-2 | Check that **related indicators are consistent** with each other. | At least one cross-indicator check exists, for example GDP ÷ population ≈ GDP per capita, within a documented tolerance. |
| FR-DQ-3 | Tests run **without calling the live API**. | The test suite passes offline. |

## 6. Non-functional requirements

| ID                         | Requirement                                                                                                                                                                                                                                                                                             | Acceptance criteria                                                                  |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| NFR-1 Traceability         | Every output value is traceable to the API response it came from.                                                                                                                                                                                                                                       | Any final value can be traced to a specific stored response.                         |
| NFR-2 Idempotency          | A re-run with unchanged source data creates **no duplicate analytical records**.                                                                                                                                                                                                                        | Running twice gives identical analytical outputs; the business key is unique.        |
| NFR-3 Missing ≠ zero       | Missing data is treated as a meaningful outcome, not as zero.                                                                                                                                                                                                                                           | No missing value is stored or reported as 0; missing values are distinguishable from real values and from zero. |
| NFR-4 Configuration-driven | A country or indicator can be added through **configuration** or documented parameters, without copying pipeline code. Scope (countries, indicators, years) is driven by configuration. *(The brief lists this under §2; it is a cross-cutting quality of ingestion, transformation, DQ, and serving.)* | Adding a country or indicator changes only configuration; a test or demo proves it.  |
| NFR-5 Local only           | Runs locally; no cloud resources, paid accounts, or API accounts. Docker is allowed.                                                                                                                                                                                                                    | No credentials are needed anywhere.                                                  |
| NFR-6 Reproducibility | A **single documented command** runs the whole pipeline locally from a clean checkout, by following the README. *(The brief lists this under §1; it applies to the whole pipeline, not only ingestion.)* | Following the README on a fresh clone produces the outputs with one command. |

## 7. Constraints

- Any language or stack.
- Suggested time box: 4–6 hours. Stop at the limit and document unfinished work and next steps.

## 8. Priorities

If time runs short, deliver in this order:

1. Correct, idempotent ingestion and a clearly defined data model (FR-ING-*, FR-MOD-*, NFR-1 to NFR-4, NFR-6)
2. Data-quality checks and tests (FR-DQ-*)
3. The required analytics outputs (FR-ANA-1 to FR-ANA-4)
4. README, production design note, and walkthrough (see [§11](#11-deliverables))
5. Anything optional (FR-ANA-5)

## 9. Open questions (ambiguities in the source)

These are not answered by the brief. Each is resolved by a decision or assumption in [`decisions.md`](decisions.md).

| ID | Question | Resolved by |
|---|---|---|
| Q1 | What counts as **"incomplete"** compared with "missing"? (A null value? An absent row? Partial coverage across years?) | [ADR-0008](decisions.md#adr-0008-definitions-of-missing-and-incomplete-data) |
| Q2 | Does **"latest available year"** mean each country's own latest year, or one common year across countries? | [ADR-0009](decisions.md#adr-0009-analytics-interpretations-latest-year-income-group-aggregation-year-over-year) |
| Q3 | Which **income-group classification** applies to each year? (The API provides only the current classification.) | [ADR-0011](decisions.md#adr-0011-current-income-classification-applies-to-every-year) |
| Q4 | How should **income groups be aggregated** (sum, mean, population-weighted), and how are countries with missing data handled? | [ADR-0009](decisions.md#adr-0009-analytics-interpretations-latest-year-income-group-aggregation-year-over-year) |
| Q5 | What is the YoY result for **2018**, whose prior year (2017) falls outside the stated range? | [ADR-0009](decisions.md#adr-0009-analytics-interpretations-latest-year-income-group-aggregation-year-over-year) |
| Q6 | What **tolerance** applies to cross-indicator consistency checks? | [ADR-0010](decisions.md#adr-0010-gdp-consistency-check-with-a-01-tolerance) |
| Q7 | If the source **revises** a value between runs, is that "unchanged source data"? Which value wins? | [ADR-0006](decisions.md#adr-0006-fetch-the-full-scope-every-run-keep-every-run-latest-run-wins) |

## 10. Requirements traceability matrix

Updated as requirements are implemented. Paths are relative to `pipelines/worldbank/` unless they start with `pipelines/` or `docs/`.

| Requirement | Implemented in | Verified by |
|---|---|---|
| FR-ING-1 | TBD | TBD |
| FR-ING-2 | TBD | TBD |
| FR-ING-3 | `src/worldbank/client.py`: follows every page; checks page consistency and row totals | `tests/test_client.py` |
| FR-ING-4 | Partial: transient errors retried with backoff (`src/worldbank/client.py`); error bodies and malformed responses detected (`src/worldbank/models.py`) | `tests/test_client.py`, `tests/test_models.py` |
| FR-MOD-1 | TBD | TBD |
| FR-MOD-2 | TBD | TBD |
| FR-MOD-3 | TBD | TBD |
| FR-ANA-1 | TBD | TBD |
| FR-ANA-2 | TBD | TBD |
| FR-ANA-3 | TBD | TBD |
| FR-ANA-4 | TBD | TBD |
| FR-DQ-1 | TBD | TBD |
| FR-DQ-2 | TBD | TBD |
| FR-DQ-3 | TBD | TBD |
| NFR-1 | Partial: each landed page gets a stable response ID and a manifest entry (URL, fetch time, sha256) in `src/worldbank/landing.py` | `tests/test_landing.py` |
| NFR-2 | TBD | TBD |
| NFR-3 | Partial: API values never coerced (`src/worldbank/models.py`) | `tests/test_models.py` |
| NFR-4 | Partial: scope defined in `config.yml`, validated by `src/worldbank/config.py` | `tests/test_config.py` |
| NFR-5 | TBD | TBD |
| NFR-6 | TBD | TBD |

## 11. Deliverables

The evaluation side of the brief (brief §5, §6, and Notes): our definition of done.

### Repository

- [ ] Git/GitHub repository, with commit history, containing all the deliverables below
- [ ] One documented command runs the pipeline locally from a clean checkout, following the README (NFR-6)
- [ ] Sample output of the reporting queries is committed (for example, CSV)

### README sections

- [ ] Setup instructions
- [ ] Assumptions (resolves the §9 open questions)
- [ ] Trade-offs
- [ ] Short walkthrough of key decisions
- [ ] AI usage
- [ ] Data model: grain, business keys, relationships (FR-MOD-2)
- [ ] How to add a country or indicator (NFR-4)
- [ ] Unfinished work and next steps, if the time box is reached

### Production design note (README, about one page, bullets are fine)

- [ ] Scheduling and incremental refreshes
- [ ] Handling late, corrected, or changed source data
- [ ] Monitoring, alerting, and data-quality failures
- [ ] Backfills and replay-ability
- [ ] Mapping to Snowflake plus AWS Glue or EMR, or to comparable Azure services

### Evaluation focus (from the Notes)

- Correctness, structure, and clarity
- **Correct, idempotent ingestion and a clear data model matter the most**
- Time box and priority order: see [§7](#7-constraints) and [§8](#8-priorities)
