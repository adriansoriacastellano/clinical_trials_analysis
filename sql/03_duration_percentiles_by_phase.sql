-- =============================================================================
-- Query:   Trial duration percentiles by phase
-- Question: Beyond the average, how does the full distribution of trial
--           duration differ across phases? Are the tails of the distribution
--           (slow-running Phase III trials, e.g.) hiding behind the mean?
-- Technique: ordered-set aggregate functions (percentile_cont).
-- Tables:   fct_clinical_trials, brg_trial_phase, dim_phase
-- Notes:
--   - Restricted to completed trials with a non-null duration_days (start to
--     completion), and to the four main phases (is_main_phase), consistent
--     with the dataset's stated scope (Phases I-IV).
--   - A trial can belong to more than one phase (bridge table), so it can
--     contribute its duration to more than one phase's distribution.
-- =============================================================================

select
    p.phase_label,
    count(*)                                                              as completed_trials,
    round(avg(f.duration_days), 0)                                        as avg_duration_days,
    percentile_cont(0.25) within group (order by f.duration_days)         as p25_duration_days,
    percentile_cont(0.5)  within group (order by f.duration_days)         as median_duration_days,
    percentile_cont(0.75) within group (order by f.duration_days)         as p75_duration_days,
    percentile_cont(0.9)  within group (order by f.duration_days)         as p90_duration_days
from fct_clinical_trials f
inner join brg_trial_phase bp on f.nct_id = bp.nct_id
inner join dim_phase p on bp.phase_id = p.phase_id
where f.is_completed = true
  and f.duration_days is not null
  and p.is_main_phase = true
group by p.phase_label
order by median_duration_days;
