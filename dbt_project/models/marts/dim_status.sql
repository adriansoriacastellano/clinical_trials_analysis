with source as (
    select distinct overall_status
    from {{ ref('stg_clinical_trials') }}
)

select
    row_number() over (order by overall_status) as status_id,
    overall_status                              as status_code,
    case
        when overall_status = 'COMPLETED' then 'Completed'
        when overall_status = 'TERMINATED' then 'Terminated'
        when overall_status = 'WITHDRAWN' then 'Withdrawn'
        when overall_status = 'SUSPENDED' then 'Suspended'
        when overall_status = 'RECRUITING' then 'Recruiting'
        when overall_status = 'ACTIVE_NOT_RECRUITING' then 'Active, not recruiting'
        when overall_status = 'NOT_YET_RECRUITING' then 'Not yet recruiting'
        when overall_status = 'ENROLLING_BY_INVITATION' then 'Enrolling by invitation'
        when overall_status = 'UNKNOWN' then 'Unknown'
        else overall_status
    end                                         as status_label,
    case
        when overall_status = 'COMPLETED' then true
        else false
    end                                         as is_completed,
    case
        when overall_status in ('TERMINATED', 'WITHDRAWN', 'SUSPENDED') then true
        else false
    end                                         as is_abandoned,
    case
        when overall_status in ('COMPLETED', 'TERMINATED', 'WITHDRAWN', 'SUSPENDED') then true
        else false
    end                                         as is_concluded
from source
