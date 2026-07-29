import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    aws_region: str
    bucket_name: str
    warehouse_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        aws_region = os.environ.get("AWS_REGION", "us-east-1")
        bucket_name = os.environ["LAKEHOUSE_BUCKET_NAME"]
        return cls(
            aws_region=aws_region,
            bucket_name=bucket_name,
            warehouse_path=f"s3://{bucket_name}/warehouse/",
        )
