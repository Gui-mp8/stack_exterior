from __future__ import annotations

import boto3
from airflow.sdk import task


@task
def ensure_s3_prefix(config: dict) -> str:
    s3 = boto3.client("s3", region_name=config["aws_region"])
    bucket = config["s3_bucket"]
    prefix = f"{config['s3_prefix'].strip('/')}/"

    s3.head_bucket(Bucket=bucket)

    response = s3.list_objects_v2(
        Bucket=bucket,
        Prefix=prefix,
        MaxKeys=1,
    )

    if response.get("KeyCount", 0) == 0:
        s3.put_object(
            Bucket=bucket,
            Key=prefix,
            Body=b"",
        )

    return f"s3://{bucket}/{prefix}"
