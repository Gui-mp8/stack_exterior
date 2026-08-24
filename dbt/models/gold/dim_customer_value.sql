{{ config(materialized='table') }}

with customer_orders as (
    select
        orders.customer_id,
        count(distinct orders.order_id) as order_count,
        max(orders.order_date) as last_order_at,
        cast(sum(items.total_amount) as decimal(18, 2)) as lifetime_value
    from {{ ref('stg_orders') }} as orders
    inner join {{ ref('stg_order_items') }} as items
        on orders.order_id = items.order_id
    where orders.status != 'cancelled'
    group by 1
)

select
    customers.customer_id,
    customers.customer_name,
    customers.state,
    customers.customer_segment,
    coalesce(customer_orders.order_count, 0) as order_count,
    customer_orders.last_order_at,
    coalesce(customer_orders.lifetime_value, cast(0 as decimal(18, 2))) as lifetime_value
from {{ ref('stg_customers') }} as customers
left join customer_orders
    on customers.customer_id = customer_orders.customer_id
