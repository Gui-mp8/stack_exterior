from __future__ import annotations

import os
from datetime import datetime

from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import dag
from include.settings import BRONZE_CONFIG
from include.tasks.s3 import ensure_s3_prefix
from include.task_groups.glue_catalog import TaskFactoryGlueCatalogTG


@dag(
    dag_id="dag_test_stack_bronze",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["stack_exterior", "bronze", "s3", "glue"],
)
def bronze_pipeline():
    generate_bronze_data = DockerOperator(
        task_id="generate_bronze_data",
        image=BRONZE_CONFIG["generator_image"],
        api_version="auto",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        auto_remove="success",
        mount_tmp_dir=False,
        environment={
            "AWS_DEFAULT_REGION": BRONZE_CONFIG["aws_region"],
            "S3_BUCKET": BRONZE_CONFIG["s3_bucket"],
            "S3_BRONZE_PREFIX": BRONZE_CONFIG["s3_prefix"],
            "ROWS_PER_FILE": BRONZE_CONFIG["rows_per_file"],
        },
        private_environment={
            "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID", ""),
            "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
            "AWS_SESSION_TOKEN": os.environ.get("AWS_SESSION_TOKEN", ""),
        },
    )

    s3_prefix = ensure_s3_prefix(BRONZE_CONFIG)

    glue_catalog = TaskFactoryGlueCatalogTG(
        group_id="configure_glue_catalog",
        config=BRONZE_CONFIG,
    )

    s3_prefix >> generate_bronze_data >> glue_catalog


bronze_pipeline()
