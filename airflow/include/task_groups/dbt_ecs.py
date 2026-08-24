from __future__ import annotations

from datetime import timedelta
from typing import Optional

from airflow.providers.amazon.aws.operators.ecs import EcsRunTaskOperator
from airflow.sdk import Asset, TaskGroup


class TaskFactoryDbtEcsTG(TaskGroup):
    def __init__(
        self,
        group_id: str,
        config: dict,
        selector: str,
        outlet: Asset,
        tooltip: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            group_id=group_id,
            tooltip=tooltip or f"Executa dbt {selector} no ECS Fargate",
            **kwargs,
        )

        run_dbt = EcsRunTaskOperator(
            task_id="run_dbt",
            cluster=config["cluster"],
            task_definition=config["task_definition"],
            launch_type="FARGATE",
            overrides={
                "containerOverrides": [
                    {
                        "name": config["container_name"],
                        "command": ["build", "--select", selector],
                    }
                ]
            },
            network_configuration={
                "awsvpcConfiguration": {
                    "subnets": config["subnets"],
                    "securityGroups": config["security_groups"],
                    "assignPublicIp": config["assign_public_ip"],
                }
            },
            aws_conn_id=config["aws_conn_id"],
            region_name=config["aws_region"],
            awslogs_group=config["log_group"],
            awslogs_region=config["aws_region"],
            awslogs_stream_prefix=config["log_stream_prefix"],
            reattach=True,
            wait_for_completion=True,
            execution_timeout=timedelta(hours=2),
            outlets=[outlet],
            task_group=self,
        )

        run_dbt
