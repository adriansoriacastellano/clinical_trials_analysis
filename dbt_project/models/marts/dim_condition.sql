select
    row_number() over (order by condition_name_normalized, condition_name_raw) as condition_id,
    condition_name_raw,
    condition_name_normalized
from {{ ref('int_condition_normalized') }}
