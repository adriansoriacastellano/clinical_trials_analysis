with condition_list as (
    select distinct
        unnest(string_split(conditions, '|')) as condition_name
    from {{ ref('stg_clinical_trials') }}
    where conditions is not null and conditions != ''
),

cleaned as (
    select distinct
        trim(condition_name) as condition_name
    from condition_list
    where condition_name != ''
)

select
    row_number() over (order by condition_name) as condition_id,
    condition_name
from cleaned
