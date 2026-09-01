# Streamlit dashboard

A live companion to the Power BI dashboard, reading directly from BigQuery. See
"A Live View: Streamlit + BigQuery" in the [root README](../README.md) for how
this fits into the rest of the project.

## Structure

```
streamlit_app/
├── streamlit_app.py   # entry point / Overview page
├── pages/
│   ├── 1_📊_Factors_I.py    # Phase, Intervention Type, Sponsor
│   └── 2_🌍_Factors_II.py   # Enrollment, Condition, Country
├── data.py             # BigQuery client + every query, cached
├── theme.py            # navy/mint palette + shared Plotly layout
└── requirements.txt    # deliberately minimal — just what this app imports
```

## Run it locally

1. Copy `.streamlit/secrets.toml.example` (repo root) to `.streamlit/secrets.toml`
   and fill in your BigQuery project and service account key — see
   [BigQuery (Optional Cloud Warehouse)](../README.md#bigquery-optional-cloud-warehouse)
   for how to create one. `.streamlit/secrets.toml` is gitignored; never commit it.
2. `pip install -r streamlit_app/requirements.txt`
3. `streamlit run streamlit_app/streamlit_app.py`

## Why a separate requirements.txt

The root `requirements.txt` carries dbt, Jupyter, and every notebook dependency —
fine for local development, wasteful for Streamlit Community Cloud's build step.
This one lists only what the app itself imports.
