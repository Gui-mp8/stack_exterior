{{
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='order_id',
    on_schema_change='sync_all_columns',
    partitioned_by=['month(order_date)']
  )
}}

with ranked as (
    select
        order_id,
        customer_id,
        order_date,
        lower(trim(status)) as status,
        lower(trim(channel)) as channel,
        lower(trim(payment_method)) as payment_method,
        row_number() over (
            partition by order_id
            order by order_date desc
        ) as row_number
    from {{ source('bronze', 'orders') }}
)

select
    order_id,
    customer_id,
    order_date,
    status,
    channel,
    payment_method
from ranked
where row_number = 1
