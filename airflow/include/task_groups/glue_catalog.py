from __future__ import annotations

from typing import Optional

import boto3
from airflow.sdk import TaskGroup, task
from botocore.exceptions import ClientError


PARQUET_INPUT_FORMAT = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
PARQUET_OUTPUT_FORMAT = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
PARQUET_SERDE = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"


@task
def ensure_glue_database(config: dict) -> str:
    glue = boto3.client("glue", region_name=config["aws_region"])

    try:
        glue.create_database(
            DatabaseInput={
                "Name": config["glue_database"],
                "Description": "Bronze database for stack_exterior raw parquet data.",
            }
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "AlreadyExistsException":
            raise

    return config["glue_database"]


@task
def upsert_glue_tables(config: dict) -> list[str]:
    glue = boto3.client("glue", region_name=config["aws_region"])
    table_names = []

    for table_name, columns in config["tables"].items():
        table_input = {
            "Name": table_name,
            "TableType": "EXTERNAL_TABLE",
            "Parameters": {
                "EXTERNAL": "TRUE",
                "classification": "parquet",
            },
            "StorageDescriptor": {
                "Columns": columns,
                "Location": (
                    f"s3://{config['s3_bucket']}/"
                    f"{config['s3_prefix'].strip('/')}/{table_name}/"
                ),
                "InputFormat": PARQUET_INPUT_FORMAT,
                "OutputFormat": PARQUET_OUTPUT_FORMAT,
                "Compressed": True,
                "SerdeInfo": {
                    "SerializationLibrary": PARQUET_SERDE,
                },
            },
        }

        try:
            glue.create_table(
                DatabaseName=config["glue_database"],
                TableInput=table_input,
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "AlreadyExistsException":
                raise
            glue.update_table(
                DatabaseName=config["glue_database"],
                TableInput=table_input,
            )

        table_names.append(table_name)

    return table_names


class TaskFactoryGlueCatalogTG(TaskGroup):
    def __init__(
        self,
        group_id: str,
        config: dict,
        tooltip: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            group_id=group_id,
            tooltip=tooltip or "Configura Glue Catalog para a camada bronze",
            **kwargs,
        )

        database = ensure_glue_database.override(task_group=self)(config)
        tables = upsert_glue_tables.override(task_group=self)(config)

        database >> tables
