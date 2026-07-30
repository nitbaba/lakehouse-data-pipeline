import os

import boto3
from pyspark.sql import SparkSession

CATALOG = "rest"


def build_spark_session(app_name: str) -> SparkSession:
    # AWS SDK v1 (used by Spark's Hadoop S3A connector) can't resolve our
    # assumable-role AWS CLI profile on its own — see docker/spark/spark-defaults.conf
    # for why. boto3 resolves it correctly, so we assume the role ourselves
    # and hand Spark ready-made temporary credentials.
    profile = os.environ.get("AWS_PROFILE")
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    credentials = session.get_credentials()
    if credentials is None:
        raise RuntimeError("no AWS credentials resolved for boto3 session")
    frozen = credentials.get_frozen_credentials()

    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.hadoop.fs.s3a.access.key", frozen.access_key)
        .config("spark.hadoop.fs.s3a.secret.key", frozen.secret_key)
    )
    if frozen.token:
        builder = builder.config("spark.hadoop.fs.s3a.session.token", frozen.token)
    return builder.getOrCreate()
