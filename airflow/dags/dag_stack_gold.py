from __future__ import annotations

from datetime import datetime

from airflow.sdk import dag
from include.assets import GOLD_READY, SILVER_READY
from include.settings import ECS_DBT_CONFIG
from include.task_groups.dbt_ecs import TaskFactoryDbtEcsTG


@dag(
    dag_id="dag_stack_gold",
    start_date=datetime(2026, 1, 1),
    schedule=[SILVER_READY],
    catchup=False,
    tags=["stack_exterior", "gold", "dbt", "ecs", "fargate", "iceberg"],
)
def gold_pipeline():
    TaskFactoryDbtEcsTG(
        group_id="transform_gold",
        config=ECS_DBT_CONFIG,
        selector="path:models/gold",
        outlet=GOLD_READY,
    )


gold_pipeline()
