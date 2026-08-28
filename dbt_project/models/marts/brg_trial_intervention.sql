{% if target.type == 'bigquery' %}

select
    s.nct_id,
    i.intervention_type_id,
    i.intervention_name
from {{ ref('stg_clinical_trials') }} s
cross join unnest(json_value_array(s.intervention_types)) as raw_intervention_name
inner join {{ ref('dim_intervention_type') }} i
    on trim(raw_intervention_name) = i.intervention_name
where s.intervention_types is not null
  and s.intervention_types != '[]'
  and s.intervention_types != ''

{% else %}

select
    s.nct_id,
    i.intervention_type_id,
    i.intervention_name
from {{ ref('stg_clinical_trials') }} s
cross join unnest(from_json(s.intervention_types, '["VARCHAR"]')) as t(intervention_name)
inner join {{ ref('dim_intervention_type') }} i
    on trim(t.intervention_name) = i.intervention_name
where s.intervention_types is not null
  and s.intervention_types != '[]'
  and s.intervention_types != ''

{% endif %}
