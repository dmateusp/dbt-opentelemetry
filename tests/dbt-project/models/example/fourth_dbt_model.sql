select *
from {{ ref("my_second_dbt_model") }}
union all
select *
from {{ ref("third_dbt_model") }}
