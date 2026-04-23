import json
import logging
import os
import sys

import boto3
from botocore.config import Config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def get_env_variables():
    return {
        "minio_endpoint": os.environ.get("MINIO_ENDPOINT", ""),
        "aws_access_key": os.environ.get("AWS_ACCESS_KEY_ID", ""),
        "aws_secret_key": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
        "bucket": os.environ["BUCKET"],
        "object_key": os.environ["OBJECT_KEY"],
        "expected_records": os.environ["EXPECTED_RECORDS"],
    }


def create_s3_client(endpoint: str, access_key: str, secret_key: str):
    if endpoint:
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="eu-west-1",
            config=Config(s3={"addressing_style": "path"}),
        )
    else:
        return boto3.client(
            "s3",
            region_name="eu-west-1",
        )


def download_payload(s3_client, bucket: str, object_key: str) -> dict:
    logger.info("Downloading payload from s3://%s/%s", bucket, object_key)
    response = s3_client.get_object(Bucket=bucket, Key=object_key)
    payload_bytes = response["Body"].read()
    return json.loads(payload_bytes.decode("utf-8"))


def validate_total_records(payload: dict, expected_records: int) -> None:
    total_records = payload.get("total_records")
    logger.info(
        "Validating payload total_records=%s against expected_records=%s",
        total_records,
        expected_records,
    )

    if total_records != expected_records:
        logger.error(
            "Validation failed: total_records=%s does not match expected_records=%s",
            total_records,
            expected_records,
        )
        sys.exit(1)


def main() -> None:
    env = get_env_variables()
    expected_records = int(env["expected_records"])

    logger.info(
        "Starting validation for s3://%s/%s via endpoint=%s",
        env["bucket"],
        env["object_key"],
        env["minio_endpoint"] or "aws-s3",
    )

    s3_client = create_s3_client(
        endpoint=env["minio_endpoint"],
        access_key=env["aws_access_key"],
        secret_key=env["aws_secret_key"],
    )
    payload = download_payload(
        s3_client=s3_client,
        bucket=env["bucket"],
        object_key=env["object_key"],
    )
    validate_total_records(payload, expected_records)

    logger.info("Validation finished successfully")


if __name__ == "__main__":
    main()
