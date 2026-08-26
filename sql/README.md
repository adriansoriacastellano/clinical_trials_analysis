# `/sql` — Standalone ad-hoc queries

This folder holds independent, hand-written SQL queries against the **mart tables** produced by the dbt project (`dbt_project/models/marts/`). They are not part of the dbt DAG — nothing here is `ref()`'d, run by `dbt run`, or covered by `dbt test`.

## Why this exists

The dashboard and the dbt tests answer *"is the pipeline correct and does it match the reporting layer?"*. These queries answer a different, complementary question: *"can I re-derive these same numbers with nothing but raw SQL against the warehouse?"* — a quick way to sanity-check a finding, explore a follow-up question, or hand a reviewer something they can run in seconds without opening Power BI or a notebook. It's the same independent-tie-out philosophy behind the EDA notebook (`notebooks/01_exploration_SLA.ipynb`), just at SQL-snippet scale instead of full analysis scale.

## How to run

Table names are deliberately **unqualified** (`fct_clinical_trials`, not `main.fct_clinical_trials`) so these queries aren't hardcoded to dbt-duckdb's current default schema — they resolve against whatever schema is active on your connection. From the repo root, with the dbt pipeline already built at least once (`cd dbt_project && dbt seed && dbt run`):

```bash
duckdb data/dwh_dev.duckdb < sql/01_country_completion_ranking.sql
```

or, from Python:

```python
import duckdb
con = duckdb.connect("data/dwh_dev.duckdb", read_only=True)
con.execute(open("sql/01_country_completion_ranking.sql").read()).df()
```

Both connect straight to the warehouse file, so the active schema is whichever one dbt materialized the marts into — currently `main` (dbt-duckdb's default, since this project sets no custom `generate_schema_name` macro). If that ever changes, or you're running these against a database where the marts live under a different schema, set it once per session before running any query in this folder:

```sql
USE my_other_schema;
```

## Queries

| File | Business question | SQL technique |
|---|---|---|
| `01_country_completion_ranking.sql` | Which countries complete trials most reliably, above a basic volume floor? | Window function (`RANK() OVER`) |
| `02_maturity_bias_adjustment.sql` | Is the mid-period dip in completion rate real, or an artefact of recently-started trials not having concluded yet? | Nested CTEs |
| `03_duration_percentiles_by_phase.sql` | How does the full distribution (not just the average) of trial duration differ by phase? | Ordered-set aggregates (`percentile_cont`) |
| `04_enrollment_band_abandonment_cliff.sql` | Is abandonment risk a smooth gradient across trial size, or a cliff at very small trials? | `CASE`-based bucketing |
| `05_intervention_type_completion_spread.sql` | Which intervention types complete most/least reliably, and how far from the category average? | Window aggregates (`AVG`/`MIN`/`MAX OVER`) |
| `06_sponsor_class_completion_vs_volume.sql` | Does the industry-vs-NIH completion gap hold once low-volume sponsor classes are filtered out? | Aggregation + `HAVING` threshold |

Each file starts with a header comment stating the business question it answers, the technique it demonstrates, the tables it touches, and any thresholds or assumptions (e.g. minimum trial counts for representativeness) — read that before trusting the numbers for anything beyond a quick check.

## Scope note

These are read-only, exploratory queries against already-modelled marts. They intentionally duplicate a small amount of logic that also lives in dbt/Power BI (e.g. completion-rate math) — that duplication is the point, not a maintenance target. If a query here needs to become a persisted, tested, reusable transformation, it belongs in `dbt_project/models/`, not here.
