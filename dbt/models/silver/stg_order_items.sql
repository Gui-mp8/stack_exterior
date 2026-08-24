{{
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='order_item_id',
    on_schema_change='sync_all_columns'
  )
}}

with ranked as (
    select
        order_item_id,
        order_id,
        product_id,
        lower(trim(category)) as category,
        quantity,
        cast(unit_price as decimal(18, 2)) as unit_price,
        cast(discount_percentage as decimal(5, 4)) as discount_percentage,
        cast(total_amount as decimal(18, 2)) as total_amount,
        row_number() over (
            partition by order_item_id
            order by order_item_id
        ) as row_number
    from {{ source('bronze', 'order_items') }}
)

select
    order_item_id,
    order_id,
    product_id,
    category,
    quantity,
    unit_price,
    discount_percentage,
    total_amount
from ranked
where row_number = 1
