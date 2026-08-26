-- =============================================================================
-- Query:   Abandonment rate by enrollment band
-- Question: Is the relationship between trial size and abandonment risk a
--           smooth gradient, or is there a cliff at very small trials?
-- Technique: CASE-based bucketing into an ad-hoc dimension, custom sort order.
-- Tables:   fct_clinical_trials
-- Notes:
--   - Bands match the six enrollment bands used in the dashboard (README,
--     Finding 3): <50, 50-99, 100-199, 200-499, 500-999, 1,000+.
--   - Trials with a null enrollment_count are excluded rather than binned,
--     since we can't place them in a band without guessing.
-- =============================================================================

with banded as (
    select
        f.nct_id,
        f.is_completed,
        f.is_abandoned,
        case
            when f.enrollment_count < 50   then '<50'
            when f.enrollment_count < 100  then '50-99'
            when f.enrollment_count < 200  then '100-199'
            when f.enrollment_count < 500  then '200-499'
            when f.enrollment_count < 1000 then '500-999'
            else '1,000+'
        end as enrollment_band
    from fct_clinical_trials f
    where f.enrollment_count is not null
)

select
    enrollment_band,
    count(*)                                                                as total_trials,
    round(100.0 * sum(case when is_completed then 1 else 0 end) / count(*), 1) as completion_rate_pct,
    round(100.0 * sum(case when is_abandoned then 1 else 0 end) / count(*), 1)  as abandonment_rate_pct
from banded
group by enrollment_band
order by
    case enrollment_band
        when '<50'     then 1
        when '50-99'   then 2
        when '100-199' then 3
        when '200-499' then 4
        when '500-999' then 5
        else 6
    end;
