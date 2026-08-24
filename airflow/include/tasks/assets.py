from airflow.sdk import task

from include.assets import BRONZE_READY


@task(outlets=[BRONZE_READY])
def publish_bronze_ready() -> str:
    return BRONZE_READY.uri
