select
    nct_id,
    enrollment_count
from {{ ref('fct_clinical_trials') }}
where enrollment_count is not null
  and enrollment_count < 0
