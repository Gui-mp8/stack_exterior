{{
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='customer_id',
    on_schema_change='sync_all_columns'
  )
}}

with ranked as (
    select
        customer_id,
        trim(name) as customer_name,
        upper(trim(state)) as state,
        birth_year,
        created_at,
        lower(trim(customer_segment)) as customer_segment,
        row_number() over (
            partition by customer_id
            order by created_at desc
        ) as row_number
    from {{ source('bronze', 'customers') }}
)

select
    customer_id,
    customer_name,
    state,
    birth_year,
    created_at,
    customer_segment
from ranked
where row_number = 1
