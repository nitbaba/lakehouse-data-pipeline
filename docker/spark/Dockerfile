FROM tabulario/spark-iceberg:latest

# The base image bundles Iceberg's own S3FileIO (used for catalog/table I/O)
# but no Hadoop S3A support, so Spark can't do generic `s3a://` file reads
# (needed to read raw landing-zone JSON for the Bronze layer). Add it.
# Version pairing is strict: hadoop-aws 3.3.4 (matching the bundled Hadoop
# client) requires aws-java-sdk-bundle 1.12.262 specifically.
ARG HADOOP_AWS_VERSION=3.3.4
ARG AWS_SDK_BUNDLE_VERSION=1.12.262

ADD https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_BUNDLE_VERSION}/aws-java-sdk-bundle-${AWS_SDK_BUNDLE_VERSION}.jar /opt/spark/jars/

# AWS SDK v1 (used by hadoop-aws) can't resolve our assumable-role profile
# (it only reads ~/.aws/credentials, not ~/.aws/config where role_arn lives).
# boto3 handles this profile correctly, so job code assumes the role itself
# and hands Spark ready-made temporary credentials instead.
RUN pip install --no-cache-dir boto3 great_expectations
