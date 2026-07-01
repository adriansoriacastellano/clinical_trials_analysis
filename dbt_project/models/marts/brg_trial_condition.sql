select
    s.nct_id,
    c.condition_id,
    c.condition_name_normalized as condition_name
from {{ ref('stg_clinical_trials') }} s
cross join unnest(string_split(s.conditions, '|')) as t(condition_name)
inner join {{ ref('dim_condition') }} c
    on trim(t.condition_name) = c.condition_name_raw
where s.conditions is not null and s.conditions != ''
