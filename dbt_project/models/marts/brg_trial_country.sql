select
    s.nct_id,
    c.country_id,
    trim(c.country_name) as country_name
from {{ ref('stg_clinical_trials') }} s
cross join unnest(from_json(s.countries, '["VARCHAR"]')) as country_name
inner join {{ ref('dim_country') }} c
    on trim(country_name) = c.country_name
where s.countries is not null and s.countries != '[]' and s.countries != ''
