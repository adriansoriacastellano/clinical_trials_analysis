with source as (
    select distinct lead_sponsor_class, lead_sponsor_name
    from {{ ref('stg_clinical_trials') }}
    where lead_sponsor_class is not null and lead_sponsor_class != ''
)

select
    row_number() over (order by lead_sponsor_class, lead_sponsor_name) as sponsor_id,
    lead_sponsor_class,
    coalesce(lead_sponsor_name, 'Unknown')                             as sponsor_name,
    case
        when lead_sponsor_class = 'INDUSTRY' then 'Industry'
        when lead_sponsor_class = 'NIH' then 'NIH'
        when lead_sponsor_class = 'OTHER_GOV' then 'Other Government'
        when lead_sponsor_class = 'NETWORK' then 'Network'
        when lead_sponsor_class = 'FED' then 'Federal'
        when lead_sponsor_class = 'INDIV' then 'Individual'
        when lead_sponsor_class = 'OTHER' then 'Other'
        else lead_sponsor_class
    end                                                                as sponsor_class_label
from source
