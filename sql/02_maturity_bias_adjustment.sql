-- =============================================================================
-- Query:   Maturity-bias adjustment, reproduced in standalone SQL
-- Question: Is the mid-period dip in the raw completion rate a real
--           deterioration, or an artefact of recently-registered trials not
--           having had time to conclude yet?
-- Technique: nested CTEs (aggregate by year, then derive rates from that
--           aggregate in a second CTE).
-- Tables:   fct_clinical_trials, dim_date
-- Notes:
--   - This reproduces the logic behind "Completion Rate (Concluded)" in the
--     README's Temporal Bias section: dividing by (Completed + Abandoned)
--     instead of by all trials removes still-active/recruiting trials from
--     the denominator, correcting for the maturity effect.
--   - Year is taken from the trial's start date (date_id_start), matching
--     the dashboard's temporal trend line.
-- =============================================================================

with yearly_counts as (
    select
        d.year,
        count(*)                                          as total_trials,
        count(*) filter (where f.is_completed)             as completed_trials,
        count(*) filter (where f.is_abandoned)              as abandoned_trials
    from fct_clinical_trials f
    inner join dim_date d on f.date_id_start = d.date_id
    group by d.year
),

yearly_rates as (
    select
        year,
        total_trials,
        completed_trials,
        abandoned_trials,
        completed_trials + abandoned_trials                                            as concluded_trials,
        round(100.0 * completed_trials / nullif(total_trials, 0), 1)                    as raw_completion_rate_pct,
        round(
            100.0 * completed_trials / nullif(completed_trials + abandoned_trials, 0)
        , 1)                                                                            as adjusted_completion_rate_pct
    from yearly_counts
)

select *
from yearly_rates
order by year;
