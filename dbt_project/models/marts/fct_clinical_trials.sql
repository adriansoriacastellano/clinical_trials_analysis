with stg as (
    select * from {{ ref('stg_clinical_trials') }}
),

enriched as (
    select
        s.nct_id,
        s.brief_title,
        s.official_title,
        s.overall_status,
        st.status_id,
        st.is_completed,
        st.is_abandoned,
        st.is_concluded,
        s.start_date,
        day_start.date_id  as date_id_start,
        s.primary_completion_date,
        day_compl.date_id  as date_id_primary_completion,
        s.completion_date,
        day_end.date_id    as date_id_completion,
        s.study_first_posted_date,
        day_posted.date_id as date_id_first_posted,
        s.study_type,
        s.enrollment_count,
        s.enrollment_type,
        s.lead_sponsor_class,
        sp.sponsor_id,
        s.lead_sponsor_name,
        s.is_fda_regulated_drug,
        s.is_fda_regulated_device,
        s.locations_count,
        s.brief_summary,
        s.disposition_events,
        case
            when s.start_date is not null and s.completion_date is not null
            then s.completion_date - s.start_date
            else null
        end as duration_days,
        case
            when s.primary_completion_date is not null and s.completion_date is not null
            then s.completion_date - s.primary_completion_date
            else null
        end as reporting_lag_days
    from stg s
    left join {{ ref('dim_status') }} st
        on s.overall_status = st.status_code
    left join {{ ref('dim_date') }} day_start
        on s.start_date = day_start.date_id
    left join {{ ref('dim_date') }} day_compl
        on s.primary_completion_date = day_compl.date_id
    left join {{ ref('dim_date') }} day_end
        on s.completion_date = day_end.date_id
    left join {{ ref('dim_date') }} day_posted
        on s.study_first_posted_date = day_posted.date_id
    left join {{ ref('dim_sponsor') }} sp
        on s.lead_sponsor_class = sp.lead_sponsor_class
        and coalesce(s.lead_sponsor_name, 'Unknown') = sp.sponsor_name
)

select
    nct_id,
    brief_title,
    official_title,
    overall_status,
    status_id,
    is_completed,
    is_abandoned,
    is_concluded,
    start_date,
    date_id_start,
    primary_completion_date,
    date_id_primary_completion,
    completion_date,
    date_id_completion,
    study_first_posted_date,
    date_id_first_posted,
    study_type,
    enrollment_count,
    enrollment_type,
    lead_sponsor_class,
    sponsor_id,
    lead_sponsor_name,
    is_fda_regulated_drug,
    is_fda_regulated_device,
    locations_count,
    duration_days,
    reporting_lag_days,
    brief_summary,
    disposition_events
from enriched
