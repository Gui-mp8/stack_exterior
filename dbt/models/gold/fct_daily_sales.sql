{{
  config(
    materialized='table',
    partitioned_by=['month(sale_date)']
  )
}}

select
    date(orders.order_date) as sale_date,
    orders.channel,
    orders.payment_method,
    items.category,
    count(distinct orders.order_id) as order_count,
    sum(items.quantity) as item_count,
    cast(sum(items.total_amount) as decimal(18, 2)) as gross_revenue
from {{ ref('stg_orders') }} as orders
inner join {{ ref('stg_order_items') }} as items
    on orders.order_id = items.order_id
where orders.status != 'cancelled'
group by 1, 2, 3, 4
