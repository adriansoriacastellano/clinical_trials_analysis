{% if target.type == 'bigquery' %}

select
    s.nct_id,
    c.country_id,
    c.country_name
from {{ ref('stg_clinical_trials') }} s
cross join unnest(json_value_array(s.countries)) as raw_country_name
inner join {{ ref('dim_country') }} c
    on trim(raw_country_name) = c.country_name
where s.countries is not null
  and s.countries != '[]'
  and s.countries != ''

{% else %}

select
    s.nct_id,
    c.country_id,
    c.country_name
from {{ ref('stg_clinical_trials') }} s
cross join unnest(from_json(s.countries, '["VARCHAR"]')) as t(country_name)
inner join {{ ref('dim_country') }} c
    on trim(t.country_name) = c.country_name
where s.countries is not null
  and s.countries != '[]'
  and s.countries != ''

{% endif %}
