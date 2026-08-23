import io
import os
import random
from datetime import datetime, timedelta
from multiprocessing import Pool, cpu_count

import boto3
import pandas as pd


BUCKET = os.environ.get(
    "S3_BUCKET",
    "modern-data-platform-guilherme-2026",
)
BASE_PREFIX = os.environ.get(
    "S3_BRONZE_PREFIX",
    "bronze",
).strip("/")

ROWS_PER_FILE = int(
    os.environ.get(
        "ROWS_PER_FILE",
        "3000000",
    )
)

TARGET_FILES = {
    "customers": 2,
    "orders": 4,
    "order_items": 7,
}


def upload_dataframe(df, table_name, file_number):
    s3 = boto3.client("s3")

    buffer = io.BytesIO()

    df.to_parquet(
        buffer,
        engine="pyarrow",
        compression="snappy",
        index=False,
    )

    size_mb = buffer.getbuffer().nbytes / (1024 ** 2)

    buffer.seek(0)

    key = (
        f"{BASE_PREFIX}/"
        f"{table_name}/"
        f"{table_name}_{file_number:05d}.parquet"
    )

    s3.upload_fileobj(
        buffer,
        BUCKET,
        key,
    )

    print(
        f"{table_name}_{file_number:05d} "
        f"→ {size_mb:.2f} MB"
    )

    buffer.close()

    return size_mb


def create_customers_file(file_number):
    start_id = (
        file_number * ROWS_PER_FILE
    ) + 1

    end_id = (
        start_id
        + ROWS_PER_FILE
    )

    ids = range(
        start_id,
        end_id
    )

    states = [
        "RJ",
        "SP",
        "MG",
        "ES",
        "PR",
        "SC",
        "RS",
        "BA",
        "PE",
        "GO",
    ]

    segments = [
        "bronze",
        "silver",
        "gold",
        "platinum",
    ]

    rows = []

    for customer_id in ids:
        rows.append({
            "customer_id": customer_id,

            "name":
                f"customer_{customer_id}",

            "state":
                random.choice(states),

            "birth_year":
                random.randint(
                    1950,
                    2006,
                ),

            "created_at":
                datetime(2018, 1, 1)
                + timedelta(
                    days=random.randint(
                        0,
                        3000,
                    )
                ),

            "customer_segment":
                random.choice(
                    segments
                ),
        })

    df = pd.DataFrame(rows)

    return upload_dataframe(
        df,
        "customers",
        file_number,
    )


def create_orders_file(args):
    file_number, max_customer_id = args

    start_id = (
        file_number * ROWS_PER_FILE
    ) + 1

    end_id = (
        start_id
        + ROWS_PER_FILE
    )

    statuses = [
        "created",
        "paid",
        "shipped",
        "delivered",
        "cancelled",
    ]

    channels = [
        "app",
        "website",
        "store",
        "marketplace",
    ]

    payments = [
        "credit_card",
        "pix",
        "debit_card",
        "boleto",
    ]

    start_date = datetime(
        2024,
        1,
        1,
    )

    rows = []

    for order_id in range(
        start_id,
        end_id,
    ):
        rows.append({
            "order_id":
                order_id,

            "customer_id":
                random.randint(
                    1,
                    max_customer_id,
                ),

            "order_date":
                start_date
                + timedelta(
                    days=random.randint(
                        0,
                        950,
                    ),
                    seconds=random.randint(
                        0,
                        86399,
                    ),
                ),

            "status":
                random.choice(
                    statuses
                ),

            "channel":
                random.choice(
                    channels
                ),

            "payment_method":
                random.choice(
                    payments
                ),
        })

    df = pd.DataFrame(rows)

    return upload_dataframe(
        df,
        "orders",
        file_number,
    )


def create_order_items_file(args):
    file_number, max_order_id = args

    rows = []

    start_item_id = (
        file_number
        * ROWS_PER_FILE
    ) + 1

    for i in range(
        ROWS_PER_FILE
    ):
        order_item_id = (
            start_item_id + i
        )

        quantity = random.randint(
            1,
            5,
        )

        unit_price = round(
            random.uniform(
                10,
                2000,
            ),
            2,
        )

        discount = round(
            random.uniform(
                0,
                0.30,
            ),
            2,
        )

        rows.append({
            "order_item_id":
                order_item_id,

            "order_id":
                random.randint(
                    1,
                    max_order_id,
                ),

            "product_id":
                random.randint(
                    1,
                    100_000,
                ),

            "category":
                random.choice([
                    "electronics",
                    "fashion",
                    "home",
                    "sports",
                    "books",
                    "beauty",
                    "food",
                    "pets",
                ]),

            "quantity":
                quantity,

            "unit_price":
                unit_price,

            "discount_percentage":
                discount,

            "total_amount":
                round(
                    quantity
                    * unit_price
                    * (1 - discount),
                    2,
                ),
        })

    df = pd.DataFrame(rows)

    return upload_dataframe(
        df,
        "order_items",
        file_number,
    )


def main():
    workers = 4

    print(
        f"Usando {workers} processos"
    )

    # --------------------------------------------------------
    # CUSTOMERS
    # --------------------------------------------------------

    with Pool(workers) as pool:
        pool.map(
            create_customers_file,
            range(
                TARGET_FILES[
                    "customers"
                ]
            ),
        )

    max_customer_id = (
        TARGET_FILES["customers"]
        * ROWS_PER_FILE
    )

    # --------------------------------------------------------
    # ORDERS
    # --------------------------------------------------------

    order_args = [
        (
            file_number,
            max_customer_id,
        )
        for file_number
        in range(
            TARGET_FILES[
                "orders"
            ]
        )
    ]

    with Pool(workers) as pool:
        pool.map(
            create_orders_file,
            order_args,
        )

    max_order_id = (
        TARGET_FILES["orders"]
        * ROWS_PER_FILE
    )

    # --------------------------------------------------------
    # ORDER ITEMS
    # --------------------------------------------------------

    item_args = [
        (
            file_number,
            max_order_id,
        )
        for file_number
        in range(
            TARGET_FILES[
                "order_items"
            ]
        )
    ]

    with Pool(workers) as pool:
        pool.map(
            create_order_items_file,
            item_args,
        )


if __name__ == "__main__":
    main()
