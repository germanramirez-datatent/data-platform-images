import json
import logging
import os
from datetime import date, timedelta

import boto3
import requests
from botocore.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def get_env_variables():
    return {
        "simulation_api_url": os.environ["SIMULATION_API_URL"],
        "minio_endpoint": os.environ.get("MINIO_ENDPOINT", ""),
        "aws_access_key": os.environ.get("AWS_ACCESS_KEY_ID", ""),
        "aws_secret_key": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
        "bucket": os.environ["RAW_BUCKET"],
        "center_id": os.environ["CENTER_ID"],
        "ingest_date": os.environ.get("INGEST_DATE") or (date.today() - timedelta(days=1)).isoformat(),
    }


def parse_ingest_date(ingest_date: str) -> date:
    return date.fromisoformat(ingest_date)


def build_api_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/traffic/range"


def build_query_params(center_id: str, ingest_day: date) -> dict[str, str]:
    date_str = ingest_day.isoformat()
    return {
        "center_id": center_id,
        "from": date_str,
        "to": date_str,
    }


def fetch_traffic_data(base_url: str, center_id: str, ingest_day: date) -> dict:
    api_url = build_api_url(base_url)
    params = build_query_params(center_id, ingest_day)
    logger.info("Requesting traffic data from %s with params=%s", api_url, params)

    response = requests.get(
        api_url,
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    logger.info("Traffic API responded with status_code=%s", response.status_code)
    return response.json()


def build_object_key(center_id: str, ingest_day: date) -> str:
    return (
        f"traffic/year={ingest_day.year:04d}/"
        f"month={ingest_day.month:02d}/"
        f"day={ingest_day.day:02d}/"
        f"{center_id}.json"
    )


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


def upload_to_minio(s3_client, bucket: str, object_key: str, payload: dict) -> None:
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
    with open("/tmp/object_key.txt", "w") as f:
        f.write(object_key)
    logger.info("Wrote Argo output parameter: %s", object_key)

def main() -> None:
    env = get_env_variables()
    ingest_day = parse_ingest_date(env["ingest_date"])
    logger.info(
        "Starting traffic ingestion for center_id=%s ingest_date=%s bucket=%s storage_endpoint=%s",
        env["center_id"],
        env["ingest_date"],
        env["bucket"],
        env["minio_endpoint"] or "aws-s3",
    )

    payload = fetch_traffic_data(
        base_url=env["simulation_api_url"],
        center_id=env["center_id"],
        ingest_day=ingest_day,
    )
    logger.info(
        "Fetched traffic payload with total_records=%s",
        payload.get("total_records"),
    )

    object_key = build_object_key(env["center_id"], ingest_day)
    s3_client = create_s3_client(
        endpoint=env["minio_endpoint"],
        access_key=env["aws_access_key"],
        secret_key=env["aws_secret_key"],
    )
    upload_to_minio(s3_client, env["bucket"], object_key, payload)
    write_argo_output(object_key)
    
    logger.info("Traffic ingestion finished successfully")
    logger.info("Stored traffic data in s3://%s/%s", env["bucket"], object_key)


if __name__ == "__main__":
    main()
