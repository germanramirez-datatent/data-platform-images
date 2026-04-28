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
        "validation_field_path": os.environ.get("VALIDATION_FIELD_PATH", "total_records"),
        "validation_mode": os.environ.get("VALIDATION_MODE", "value"),
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


def resolve_field_path(payload: dict, field_path: str):
    if not field_path:
        raise ValueError("Validation field path cannot be empty")

    current_value = payload
    for field_name in field_path.split("."):
        if not isinstance(current_value, dict):
            raise ValueError(
                f"Cannot resolve '{field_path}': '{field_name}' is nested under a non-object value"
            )

        if field_name not in current_value:
            raise ValueError(f"Cannot resolve '{field_path}': missing field '{field_name}'")

        current_value = current_value[field_name]

    return current_value


def get_actual_records(field_value, validation_mode: str) -> int:
    mode = validation_mode.strip().lower()

    if mode == "value":
        if isinstance(field_value, bool) or not isinstance(field_value, int):
            raise ValueError(
                f"Validation mode 'value' expects an integer field, got {type(field_value).__name__}"
            )
        return field_value

    if mode == "count":
        if not isinstance(field_value, list):
            raise ValueError(
                f"Validation mode 'count' expects a list field, got {type(field_value).__name__}"
            )
        return len(field_value)

    if mode == "gte":
        if isinstance(field_value, list):
            return len(field_value)

        if isinstance(field_value, int) and not isinstance(field_value, bool):
            return field_value

        raise ValueError(
            f"Validation mode 'gte' expects an integer or list, got {type(field_value).__name__}"
        )

    raise ValueError(f"Unsupported validation mode '{validation_mode}'. Use 'value', 'count', or 'gte'")


def validate_records(payload: dict, expected_records: int, field_path: str, validation_mode: str) -> None:
    mode = validation_mode.strip().lower()

    try:
        field_value = resolve_field_path(payload, field_path)
        actual_records = get_actual_records(field_value, mode)
    except ValueError as error:
        logger.error("Validation failed: %s", error)
        sys.exit(1)

    if mode == "gte":
        logger.info(
            "Validating payload field_path=%s mode=%s actual_records=%s against expected_minimum=%s",
            field_path,
            mode,
            actual_records,
            expected_records,
        )

        if actual_records < expected_records:
            logger.error(
                "Validation failed: actual_records=%s is less than expected_minimum=%s",
                actual_records,
                expected_records,
            )
            sys.exit(1)
        return

    logger.info(
        "Validating payload field_path=%s mode=%s actual_records=%s against expected_records=%s",
        field_path,
        mode,
        actual_records,
        expected_records,
    )

    if actual_records != expected_records:
        logger.error(
            "Validation failed: actual_records=%s does not match expected_records=%s",
            actual_records,
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
    validate_records(
        payload=payload,
        expected_records=expected_records,
        field_path=env["validation_field_path"],
        validation_mode=env["validation_mode"],
    )

    logger.info("Validation finished successfully")


if __name__ == "__main__":
    main()
