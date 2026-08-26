{% docs __overview__ %}

# Clinical Trials Analysis

dbt layer of an end-to-end analytics engineering project studying completion and abandonment patterns across 137,556 clinical trials registered in ClinicalTrials.gov (Phases I-IV, 2010-2024).

Business context, methodology, and findings live in the [project README](https://github.com/adriansoriacastellano/clinical_trials_analysis#readme) — this site documents the transformation layer that feeds them.

## Layers

- **staging** (`stg_clinical_trials`) — one row per trial, typed and validated against the raw API extract, with an explicit date-range check (2010-01-01 to 2024-12-31).
- **intermediate** (`int_condition_normalized`) — collapses raw condition strings into canonical names via a curated seed (`condition_normalization`, 3,771 mappings).
- **marts** — `fct_clinical_trials` plus 7 dimensions and 4 bridge tables, feeding the Power BI dashboard and the standalone SQL queries in `/sql`.

## Navigation

Use the `Project` tab (left sidebar) to browse by folder, or `Database` to browse by warehouse schema. Open any model for its description, columns, tests, and lineage graph.

{% enddocs %}
