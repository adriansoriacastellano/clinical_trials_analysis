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
