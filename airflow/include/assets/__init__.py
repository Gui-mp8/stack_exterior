from airflow.sdk import Asset

from include.settings import BRONZE_CONFIG


BRONZE_READY = Asset(
    f"s3://{BRONZE_CONFIG['s3_bucket']}/{BRONZE_CONFIG['s3_prefix']}/_ready"
)
SILVER_READY = Asset("glue://awsdatacatalog/stack_exterior_silver/_ready")
GOLD_READY = Asset("glue://awsdatacatalog/stack_exterior_gold/_ready")
