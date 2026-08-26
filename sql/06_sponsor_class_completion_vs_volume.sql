-- =============================================================================
-- Query:   Completion rate by sponsor class
-- Question: Do industry-sponsored trials really complete at a higher rate
--           than NIH-sponsored trials, and is that gap explained by a
--           handful of low-volume sponsor classes rather than a real signal?
-- Technique: simple aggregation with a representativeness filter (HAVING).
-- Tables:   fct_clinical_trials, dim_sponsor
-- Notes:
--   - Representativeness threshold: >= 500 trials per sponsor class, to keep
--     small/noisy classes from dominating the ranking.
--   - This is a direct standalone tie-out of the README's Finding 2
--     (Industry vs. NIH completion rates), independent of dbt/Power BI.
-- =============================================================================

with sponsor_rates as (
    select
        sp.sponsor_class_label,
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
    inner join dim_sponsor sp on f.sponsor_id = sp.sponsor_id
    group by sp.sponsor_class_label
)

select *
from sponsor_rates
where total_trials >= 500
order by completion_rate_pct desc;
