with phase_list as (
    select distinct
        unnest(string_split(phases, '|')) as phase_code
    from {{ ref('stg_clinical_trials') }}
    where phases is not null and phases != ''
),

cleaned as (
    select distinct
        trim(phase_code) as phase_code
    from phase_list
    where phase_code != ''
)

select
    row_number() over (order by phase_code) as phase_id,
    phase_code,
    case
        when phase_code = 'PHASE1' then 'Phase I'
        when phase_code = 'PHASE2' then 'Phase II'
        when phase_code = 'PHASE3' then 'Phase III'
        when phase_code = 'PHASE4' then 'Phase IV'
        when phase_code in ('EARLY_PHASE1', 'PHASE0') then 'Early Phase I'
        when phase_code = 'NA' then 'Not Applicable'
        else coalesce(phase_code, 'Unknown')
    end                                    as phase_label,
    case
        when phase_code in ('PHASE1', 'PHASE2', 'PHASE3', 'PHASE4') then true
        else false
    end                                    as is_main_phase
from cleaned
