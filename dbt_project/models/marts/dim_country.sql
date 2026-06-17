with country_list as (
    select distinct
        unnest(from_json(countries, '["VARCHAR"]')) as country_name
    from {{ ref('stg_clinical_trials') }}
    where countries is not null and countries != '[]' and countries != ''
),

cleaned as (
    select distinct
        trim(country_name) as country_name
    from country_list
    where country_name != ''
)

select
    row_number() over (order by country_name) as country_id,
    country_name
from cleaned
