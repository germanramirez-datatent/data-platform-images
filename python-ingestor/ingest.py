import json
import logging
import os
from datetime import date, timedelta

import boto3
from botocore.config import Config

from adapters import get_adapter


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def get_env_variables() -> dict[str, str]:
    return {
        "source": os.environ.get("INGEST_SOURCE", "traffic"),
        "minio_endpoint": os.environ.get("MINIO_ENDPOINT", ""),
        "aws_access_key": os.environ.get("AWS_ACCESS_KEY_ID", ""),
        "aws_secret_key": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
        "bucket": os.environ["RAW_BUCKET"],
        "ingest_date": os.environ.get("INGEST_DATE") or (date.today() - timedelta(days=1)).isoformat(),
    }


def parse_ingest_date(ingest_date: str) -> date:
    return date.fromisoformat(ingest_date)


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

    return boto3.client(
        "s3",
        region_name="eu-west-1",
    )


def upload_payload(s3_client, bucket: str, object_key: str, payload: dict) -> None:
    logger.info("Uploading payload to s3://%s/%s", bucket, object_key)
    s3_client.put_object(
        Bucket=bucket,
        Key=object_key,
        Body=json.dumps(payload, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    logger.info("Upload completed for s3://%s/%s", bucket, object_key)


def write_argo_output(object_key: str) -> None:
    # writes output parameter for Argo to pass to next step
    with open("/tmp/object_key.txt", "w") as file_handle:
        file_handle.write(object_key)
    logger.info("Wrote Argo output parameter: %s", object_key)


def main() -> None:
    env = get_env_variables()
    ingest_day = parse_ingest_date(env["ingest_date"])
    adapter = get_adapter(env["source"], logger=logger)

    logger.info(
        "Starting %s ingestion for ingest_date=%s bucket=%s storage_endpoint=%s",
        adapter.source_name,
        env["ingest_date"],
        env["bucket"],
        env["minio_endpoint"] or "aws-s3",
    )

    payload = adapter.fetch_payload(ingest_day)
    logger.info(
        "Fetched %s payload with top_level_keys=%s",
        adapter.source_name,
        list(payload.keys()),
    )

    object_key = adapter.build_object_key(ingest_day)
    s3_client = create_s3_client(
        endpoint=env["minio_endpoint"],
        access_key=env["aws_access_key"],
        secret_key=env["aws_secret_key"],
    )
    upload_payload(s3_client, env["bucket"], object_key, payload)
    write_argo_output(object_key)

    logger.info("%s ingestion finished successfully", adapter.source_name.capitalize())
    logger.info("Stored %s data in s3://%s/%s", adapter.source_name, env["bucket"], object_key)


if __name__ == "__main__":
    main()
