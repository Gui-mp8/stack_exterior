from __future__ import annotations

from typing import Optional

import boto3
from airflow.sdk import TaskGroup, task


@task
def validate_glue_database(config: dict) -> str:
    glue = boto3.client("glue", region_name=config["aws_region"])
    glue.get_database(Name=config["glue_database"])
    return config["glue_database"]


@task
def validate_iceberg_tables(config: dict) -> list[str]:
    glue = boto3.client("glue", region_name=config["aws_region"])
    validated_tables = []

    for table_name in config["tables"]:
        table = glue.get_table(
            DatabaseName=config["glue_database"],
            Name=table_name,
        )["Table"]

        parameters = table.get("Parameters", {})
        metadata_location = parameters.get("metadata_location")
        table_type = parameters.get("table_type") or parameters.get("format")
        expected_location = (
            f"s3://{config['s3_bucket']}/"
            f"{config['s3_prefix'].strip('/')}/{table_name}"
        )

        if table_type and table_type.upper() != "ICEBERG":
            raise ValueError(f"{table_name} is not registered as an Iceberg table")

        if not metadata_location:
            raise ValueError(f"{table_name} is missing Iceberg metadata_location")

        if not metadata_location.startswith(expected_location):
            raise ValueError(
                f"{table_name} metadata is outside expected location: {expected_location}"
            )

        validated_tables.append(table_name)

    return validated_tables


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
            tooltip=tooltip or "Valida tabelas Iceberg no Glue Catalog",
            **kwargs,
        )

        database = validate_glue_database.override(task_group=self)(config)
        tables = validate_iceberg_tables.override(task_group=self)(config)

        database >> tables
