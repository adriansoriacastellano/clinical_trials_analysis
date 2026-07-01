{{ config(materialized='table') }}

with raw_conditions as (
    select distinct trim(t.condition_name) as condition_name_raw
    from {{ source('raw', 'raw_clinical_trials') }} raw
    cross join unnest(string_split(raw.conditions, '|')) as t(condition_name)
    where raw.conditions is not null
      and raw.conditions != ''
      and trim(t.condition_name) != ''
),

seed_map as (
    select condition_name_raw, condition_name_normalized
    from {{ ref('condition_normalization') }}
)

select
    r.condition_name_raw,
    coalesce(s.condition_name_normalized, r.condition_name_raw) as condition_name_normalized
from raw_conditions r
left join seed_map s
    on r.condition_name_raw = s.condition_name_raw
