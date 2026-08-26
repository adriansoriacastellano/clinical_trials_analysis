-- =============================================================================
-- Query:   Country ranking by completion rate
-- Question: Which countries complete their clinical trials most reliably,
--           once we restrict to countries with enough volume to be meaningful?
-- Technique: window function (RANK) over an aggregated CTE.
-- Tables:   fct_clinical_trials, brg_trial_country, dim_country
-- Notes:
--   - Representativeness threshold: >= 500 trials per country. This is a
--     looser bar than the >= 10,500 threshold used for the four-country bar
--     chart in the dashboard (README, Finding 4) — that chart intentionally
--     compares only the largest hosts; this query ranks every country that
--     clears a basic sample-size floor.
--   - A trial can be hosted in more than one country (brg_trial_country is a
--     bridge table), so a trial may contribute to more than one row here.
-- =============================================================================

with country_rates as (
    select
        c.country_name,
        count(distinct f.nct_id)                                              as total_trials,
        round(
            100.0 * sum(case when f.is_completed then 1 else 0 end)
            / count(distinct f.nct_id)
        , 1)                                                                   as completion_rate_pct
    from fct_clinical_trials f
    inner join brg_trial_country bc on f.nct_id = bc.nct_id
    inner join dim_country c on bc.country_id = c.country_id
    group by c.country_name
    having count(distinct f.nct_id) >= 500
)

select
    rank() over (order by completion_rate_pct desc) as completion_rank,
    country_name,
    total_trials,
    completion_rate_pct
from country_rates
order by completion_rank;
