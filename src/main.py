import os
import random
from datetime import datetime, timedelta

import pyarrow as pa
from pyiceberg.catalog import load_catalog


AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
BUCKET = os.environ.get("S3_BUCKET", "modern-data-platform-guilherme-2026")
BASE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "bronze").strip("/")
DATABASE = os.environ.get("GLUE_DATABASE_NAME", "stack_exterior_bronze")
ROWS_PER_FILE = int(os.environ.get("ROWS_PER_FILE", "3000000"))

TARGET_FILES = {
    "customers": 2,
    "orders": 4,
    "order_items": 7,
}

ICEBERG_TABLE_PROPERTIES = {
    "format-version": "2",
    "write.format.default": "parquet",
    "write.parquet.compression-codec": "snappy",
}

SCHEMAS = {
    "customers": pa.schema(
        [
            pa.field("customer_id", pa.int64()),
            pa.field("name", pa.string()),
            pa.field("state", pa.string()),
            pa.field("birth_year", pa.int64()),
            pa.field("created_at", pa.timestamp("us")),
            pa.field("customer_segment", pa.string()),
        ]
    ),
    "orders": pa.schema(
        [
            pa.field("order_id", pa.int64()),
            pa.field("customer_id", pa.int64()),
            pa.field("order_date", pa.timestamp("us")),
            pa.field("status", pa.string()),
            pa.field("channel", pa.string()),
            pa.field("payment_method", pa.string()),
        ]
    ),
    "order_items": pa.schema(
        [
            pa.field("order_item_id", pa.int64()),
            pa.field("order_id", pa.int64()),
            pa.field("product_id", pa.int64()),
            pa.field("category", pa.string()),
            pa.field("quantity", pa.int64()),
            pa.field("unit_price", pa.float64()),
            pa.field("discount_percentage", pa.float64()),
            pa.field("total_amount", pa.float64()),
        ]
    ),
}


def load_glue_catalog():
    return load_catalog(
        "glue",
        type="glue",
        warehouse=f"s3://{BUCKET}/{BASE_PREFIX}",
        **{
            "client.region": AWS_REGION,
        },
    )


def load_or_create_table(catalog, table_name):
    identifier = f"{DATABASE}.{table_name}"
    location = f"s3://{BUCKET}/{BASE_PREFIX}/{table_name}"

    return catalog.create_table_if_not_exists(
        identifier=identifier,
        schema=SCHEMAS[table_name],
        location=location,
        properties=ICEBERG_TABLE_PROPERTIES,
    )


def append_rows(catalog, rows, table_name, file_number):
    table = load_or_create_table(catalog, table_name)
    arrow_table = pa.Table.from_pylist(
        rows,
        schema=SCHEMAS[table_name],
    )

    table.append(
        arrow_table,
        snapshot_properties={
            "source": "stack_exterior_generator",
            "batch": f"{table_name}_{file_number:05d}",
        },
    )

    size_mb = arrow_table.nbytes / (1024**2)
    print(f"{table_name}_{file_number:05d} -> {size_mb:.2f} MB appended to Iceberg")

    return size_mb


def create_customers_file(catalog, file_number):
    start_id = (file_number * ROWS_PER_FILE) + 1
    end_id = start_id + ROWS_PER_FILE

    states = ["RJ", "SP", "MG", "ES", "PR", "SC", "RS", "BA", "PE", "GO"]
    segments = ["bronze", "silver", "gold", "platinum"]

    rows = []
    for customer_id in range(start_id, end_id):
        rows.append(
            {
                "customer_id": customer_id,
                "name": f"customer_{customer_id}",
                "state": random.choice(states),
                "birth_year": random.randint(1950, 2006),
                "created_at": datetime(2018, 1, 1)
                + timedelta(days=random.randint(0, 3000)),
                "customer_segment": random.choice(segments),
            }
        )

    return append_rows(catalog, rows, "customers", file_number)


def create_orders_file(catalog, file_number, max_customer_id):
    start_id = (file_number * ROWS_PER_FILE) + 1
    end_id = start_id + ROWS_PER_FILE

    statuses = ["created", "paid", "shipped", "delivered", "cancelled"]
    channels = ["app", "website", "store", "marketplace"]
    payments = ["credit_card", "pix", "debit_card", "boleto"]
    start_date = datetime(2024, 1, 1)

    rows = []
    for order_id in range(start_id, end_id):
        rows.append(
            {
                "order_id": order_id,
                "customer_id": random.randint(1, max_customer_id),
                "order_date": start_date
                + timedelta(
                    days=random.randint(0, 950),
                    seconds=random.randint(0, 86399),
                ),
                "status": random.choice(statuses),
                "channel": random.choice(channels),
                "payment_method": random.choice(payments),
            }
        )

    return append_rows(catalog, rows, "orders", file_number)


def create_order_items_file(catalog, file_number, max_order_id):
    start_item_id = (file_number * ROWS_PER_FILE) + 1
    categories = [
        "electronics",
        "fashion",
        "home",
        "sports",
        "books",
        "beauty",
        "food",
        "pets",
    ]

    rows = []
    for i in range(ROWS_PER_FILE):
        order_item_id = start_item_id + i
        quantity = random.randint(1, 5)
        unit_price = round(random.uniform(10, 2000), 2)
        discount = round(random.uniform(0, 0.30), 2)

        rows.append(
            {
                "order_item_id": order_item_id,
                "order_id": random.randint(1, max_order_id),
                "product_id": random.randint(1, 100_000),
                "category": random.choice(categories),
                "quantity": quantity,
                "unit_price": unit_price,
                "discount_percentage": discount,
                "total_amount": round(quantity * unit_price * (1 - discount), 2),
            }
        )

    return append_rows(catalog, rows, "order_items", file_number)


def main():
    catalog = load_glue_catalog()
    catalog.create_namespace_if_not_exists(DATABASE)

    print(f"Writing Iceberg tables to s3://{BUCKET}/{BASE_PREFIX}")
    print(f"Glue database: {DATABASE}")
    print(f"Rows per batch: {ROWS_PER_FILE}")

    for file_number in range(TARGET_FILES["customers"]):
        create_customers_file(catalog, file_number)

    max_customer_id = TARGET_FILES["customers"] * ROWS_PER_FILE

    for file_number in range(TARGET_FILES["orders"]):
        create_orders_file(catalog, file_number, max_customer_id)

    max_order_id = TARGET_FILES["orders"] * ROWS_PER_FILE

    for file_number in range(TARGET_FILES["order_items"]):
        create_order_items_file(catalog, file_number, max_order_id)


if __name__ == "__main__":
    main()
