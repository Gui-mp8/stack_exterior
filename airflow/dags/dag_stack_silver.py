from __future__ import annotations

from datetime import datetime

from airflow.sdk import dag
from include.assets import BRONZE_READY, SILVER_READY
from include.settings import ECS_DBT_CONFIG
from include.task_groups.dbt_ecs import TaskFactoryDbtEcsTG


@dag(
    dag_id="dag_stack_silver",
    start_date=datetime(2026, 1, 1),
    schedule=[BRONZE_READY],
    catchup=False,
    tags=["stack_exterior", "silver", "dbt", "ecs", "fargate", "iceberg"],
)
def silver_pipeline():
    TaskFactoryDbtEcsTG(
        group_id="transform_silver",
        config=ECS_DBT_CONFIG,
        selector="path:models/silver",
        outlet=SILVER_READY,
    )


silver_pipeline()
