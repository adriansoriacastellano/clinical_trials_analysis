-- =============================================================================
-- Query:   Completion-rate spread across intervention types
-- Question: Which intervention types complete most/least reliably, and how
--           far does each sit from the average across intervention types?
-- Technique: window aggregate functions (AVG/MIN/MAX OVER) applied on top of
--           an already-aggregated CTE, to compare each category against the
--           whole set without a self-join.
-- Tables:   fct_clinical_trials, brg_trial_intervention, dim_intervention_type
-- Notes:
--   - Representativeness threshold: >= 500 trials per intervention type.
--   - dataset_avg_completion_rate_pct is an unweighted average of the
--     per-type rates (one vote per category), not the overall trial-level
--     completion rate — deliberately, since the question here is about
--     spread across categories, not the dataset-wide KPI.
--   - A trial can have more than one intervention type (bridge table), so it
--     can contribute to more than one row.
-- =============================================================================

with intervention_rates as (
    select
        i.intervention_name,
        count(distinct f.nct_id)                                              as total_trials,
        round(
            100.0 * sum(case when f.is_completed then 1 else 0 end)
            / count(distinct f.nct_id)
        , 1)                                                                   as completion_rate_pct,
        round(
            100.0 * sum(case when f.is_abandoned then 1 else 0 end)
            / count(distinct f.nct_id)
        , 1)                                                                   as abandonment_rate_pct
    from fct_clinical_trials f
    inner join brg_trial_intervention bi on f.nct_id = bi.nct_id
    inner join dim_intervention_type i on bi.intervention_type_id = i.intervention_type_id
    group by i.intervention_name
    having count(distinct f.nct_id) >= 500
)

select
    intervention_name,
    total_trials,
    completion_rate_pct,
    abandonment_rate_pct,
    round(avg(completion_rate_pct) over (), 1)                       as dataset_avg_completion_rate_pct,
    round(completion_rate_pct - avg(completion_rate_pct) over (), 1) as gap_vs_avg_pct,
    round(max(completion_rate_pct) over () - min(completion_rate_pct) over (), 1) as overall_spread_pct
from intervention_rates
order by completion_rate_pct desc;
