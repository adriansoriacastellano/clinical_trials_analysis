with intervention_list as (
    select distinct
        unnest(from_json(intervention_types, '["VARCHAR"]')) as intervention_name
    from {{ ref('stg_clinical_trials') }}
    where intervention_types is not null and intervention_types != '[]' and intervention_types != ''
),

cleaned as (
    select distinct
        trim(intervention_name) as intervention_name
    from intervention_list
    where intervention_name != ''
)

select
    row_number() over (order by intervention_name) as intervention_type_id,
    intervention_name
from cleaned
