with source as (
    select * from {{ source('raw', 'raw_clinical_trials') }}
),

typed as (
    select
        nct_id,
        org_study_id,
        brief_title,
        official_title,
        overall_status,
        case
            when start_date like '____-__-__' then try_cast(start_date as date)
            when start_date like '____-__' then try_cast(start_date || '-01' as date)
            else null
        end as start_date,
        start_date_type,
        case
            when primary_completion_date like '____-__-__' then try_cast(primary_completion_date as date)
            when primary_completion_date like '____-__' then try_cast(primary_completion_date || '-01' as date)
            else null
        end as primary_completion_date,
        primary_completion_date_type,
        case
            when completion_date like '____-__-__' then try_cast(completion_date as date)
            when completion_date like '____-__' then try_cast(completion_date || '-01' as date)
            else null
        end as completion_date,
        completion_date_type,
        study_first_posted_date,
        study_type,
        phases,
        primary_purpose,
        enrollment_count,
        enrollment_type,
        lead_sponsor_name,
        lead_sponsor_class,
        conditions,
        keywords,
        brief_summary,
        is_fda_regulated_drug,
        is_fda_regulated_device,
        locations_count,
        countries,
        intervention_types,
        disposition_events
    from source
)

select * from typed
