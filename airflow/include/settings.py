BRONZE_CONFIG = {
    "generator_image": "stack-exterior-gerador:latest",
    "aws_region": "us-east-1",
    "s3_bucket": "modern-data-platform-guilherme-2026",
    "s3_prefix": "bronze",
    "rows_per_file": "3000000",
    "glue_database": "stack_exterior_bronze",
    "tables": {
        "customers": [
            {"Name": "customer_id", "Type": "bigint"},
            {"Name": "name", "Type": "string"},
            {"Name": "state", "Type": "string"},
            {"Name": "birth_year", "Type": "bigint"},
            {"Name": "created_at", "Type": "timestamp"},
            {"Name": "customer_segment", "Type": "string"},
        ],
        "orders": [
            {"Name": "order_id", "Type": "bigint"},
            {"Name": "customer_id", "Type": "bigint"},
            {"Name": "order_date", "Type": "timestamp"},
            {"Name": "status", "Type": "string"},
            {"Name": "channel", "Type": "string"},
            {"Name": "payment_method", "Type": "string"},
        ],
        "order_items": [
            {"Name": "order_item_id", "Type": "bigint"},
            {"Name": "order_id", "Type": "bigint"},
            {"Name": "product_id", "Type": "bigint"},
            {"Name": "category", "Type": "string"},
            {"Name": "quantity", "Type": "bigint"},
            {"Name": "unit_price", "Type": "double"},
            {"Name": "discount_percentage", "Type": "double"},
            {"Name": "total_amount", "Type": "double"},
        ],
    },
}

ECS_DBT_CONFIG = {
    "aws_conn_id": "aws_default",
    "aws_region": "us-east-1",
    "cluster": "stack-exterior",
    "task_definition": "stack-exterior-dbt",
    "container_name": "stack-exterior-dbt",
    "subnets": ["subnet-CHANGE_ME"],
    "security_groups": ["sg-CHANGE_ME"],
    "assign_public_ip": "ENABLED",
    "log_group": "/ecs/stack-exterior-dbt",
    "log_stream_prefix": "ecs/stack-exterior-dbt",
}
