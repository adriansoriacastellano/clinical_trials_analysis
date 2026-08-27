{% if target.type == 'bigquery' %}

with date_spine as (
    select date_day
    from unnest(generate_date_array(date '2010-01-01', date '2026-12-31', interval 1 day)) as date_day
)

select
    date_day                                              as date_id,
    extract(year from date_day)                           as year,
    extract(month from date_day)                          as month,
    extract(day from date_day)                             as day,
    extract(quarter from date_day)                        as quarter,
    extract(dayofweek from date_day) - 1                  as day_of_week,
    format_date('%Y-%m', date_day)                        as year_month,
    format_date('%B %Y', date_day)                        as month_name,
    case when extract(dayofweek from date_day) in (1, 7)
        then false else true end                          as is_weekday
from date_spine

{% else %}

with date_spine as (
    select unnest(
        generate_series(
            date '2010-01-01',
            date '2026-12-31',
            interval '1 day'
        )
    ) as date_day
)

select
    date_day                                    as date_id,
    extract(year from date_day)::int            as year,
    extract(month from date_day)::int           as month,
    extract(day from date_day)::int             as day,
    extract(quarter from date_day)::int         as quarter,
    extract(dow from date_day)::int             as day_of_week,
    strftime(date_day, '%Y-%m')                  as year_month,
    strftime(date_day, '%B %Y')                  as month_name,
    case when extract(dow from date_day) in (0, 6)
        then false else true end                as is_weekday
from date_spine

{% endif %}
