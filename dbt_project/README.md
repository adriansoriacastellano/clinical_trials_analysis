# clinical_trials_analysis (dbt project)

dbt transformations for the Clinical Trials Analysis pipeline. For business context, methodology, and findings, see the [root README](../README.md).

## Layers

- **staging** (`models/staging/`) — a 1:1 typed and validated view over the raw `raw.raw_clinical_trials` source: `stg_clinical_trials` casts fields and applies date-range validation.
- **intermediate** (`models/intermediate/`) — business logic that doesn't belong in staging or a mart yet: `int_condition_normalized` deduplicates raw condition strings via the `condition_normalization` seed.
- **marts** (`models/marts/`) — the dimensional model the dashboard reads from: one fact table (`fct_clinical_trials`), 7 dimensions, and 4 bridge tables handling the many-to-many phase/country/intervention/condition relationships.

## Targets

Two targets build the same 14 models, verified row-for-row identical:

| Target | Warehouse | Command |
|---|---|---|
| `dev` (default) | DuckDB, local | `dbt build` |
| `bigquery` | BigQuery, cloud | `dbt build -t bigquery` |

See the root README's [BigQuery (Optional Cloud Warehouse)](../README.md#bigquery-optional-cloud-warehouse) section for `bigquery` target setup.

## Common commands

```bash
dbt seed    # load the condition_normalization seed
dbt run     # build all models
dbt test    # run data quality tests (48/48 passing)
dbt build   # seed + run + test, in one DAG-ordered pass
dbt docs generate && dbt docs serve   # local documentation site
```

A published copy of the docs site is kept at [adriansoriacastellano.github.io/clinical_trials_analysis](https://adriansoriacastellano.github.io/clinical_trials_analysis/) (see [Known Limitations](../README.md#known-limitations--future-work) — it's published by hand, not on every push).
