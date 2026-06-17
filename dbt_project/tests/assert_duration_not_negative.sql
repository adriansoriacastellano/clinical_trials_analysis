select
    nct_id,
    duration_days
from {{ ref('fct_clinical_trials') }}
where duration_days is not null
  and duration_days < 0
