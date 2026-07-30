import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    aws_region: str
    bucket_name: str
    warehouse_path: str
    landing_path: str
    landing_path_s3a: str

    @classmethod
    def from_env(cls) -> "Settings":
        aws_region = os.environ.get("AWS_REGION", "us-east-1")
        bucket_name = os.environ["LAKEHOUSE_BUCKET_NAME"]
        return cls(
            aws_region=aws_region,
            bucket_name=bucket_name,
            warehouse_path=f"s3://{bucket_name}/warehouse/",
            landing_path=f"s3://{bucket_name}/landing/",
            # dlt/Iceberg's S3FileIO use the `s3://` scheme; Spark's generic
            # (non-Iceberg-table) file reads go through Hadoop's S3A
            # connector instead, which needs `s3a://`.
            landing_path_s3a=f"s3a://{bucket_name}/landing/",
        )
