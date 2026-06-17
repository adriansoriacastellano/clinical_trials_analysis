select
    s.nct_id,
    c.condition_id,
    trim(c.condition_name) as condition_name
from {{ ref('stg_clinical_trials') }} s
cross join unnest(string_split(s.conditions, '|')) as condition_name
inner join {{ ref('dim_condition') }} c
    on trim(condition_name) = c.condition_name
where s.conditions is not null and s.conditions != ''
