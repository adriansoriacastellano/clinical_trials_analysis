select
    s.nct_id,
    p.phase_id,
    trim(p.phase_code) as phase_code
from {{ ref('stg_clinical_trials') }} s
cross join unnest(string_split(s.phases, '|')) as phase_code
inner join {{ ref('dim_phase') }} p
    on trim(phase_code) = p.phase_code
where s.phases is not null and s.phases != ''
