import json
from datetime import date

import ingest


class FakeS3Client:
    def __init__(self):
        self.put_object_calls = []

    def put_object(self, **kwargs):
        self.put_object_calls.append(kwargs)


def test_get_env_variables_uses_defaults_and_explicit_values(monkeypatch):
    monkeypatch.delenv("INGEST_SOURCE", raising=False)
    monkeypatch.delenv("MINIO_ENDPOINT", raising=False)
    monkeypatch.setenv("RAW_BUCKET", "raw-bucket")
    monkeypatch.setenv("INGEST_DATE", "2026-04-22")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "access")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")

    env = ingest.get_env_variables()

    assert env == {
        "source": "traffic",
        "minio_endpoint": "",
        "aws_access_key": "access",
        "aws_secret_key": "secret",
        "bucket": "raw-bucket",
        "ingest_date": "2026-04-22",
    }


def test_parse_ingest_date():
    assert ingest.parse_ingest_date("2026-04-22") == date(2026, 4, 22)


def test_create_s3_client_uses_minio_endpoint(monkeypatch):
    calls = []

    def fake_client(*args, **kwargs):
        calls.append((args, kwargs))
        return "client"

    monkeypatch.setattr(ingest.boto3, "client", fake_client)

    client = ingest.create_s3_client("http://minio:9000", "access", "secret")

    assert client == "client"
    assert calls[0][0] == ("s3",)
    assert calls[0][1]["endpoint_url"] == "http://minio:9000"
    assert calls[0][1]["aws_access_key_id"] == "access"
    assert calls[0][1]["aws_secret_access_key"] == "secret"


def test_create_s3_client_uses_aws_s3_when_endpoint_is_empty(monkeypatch):
    calls = []

    def fake_client(*args, **kwargs):
        calls.append((args, kwargs))
        return "client"

    monkeypatch.setattr(ingest.boto3, "client", fake_client)

    client = ingest.create_s3_client("", "access", "secret")

    assert client == "client"
    assert calls[0][0] == ("s3",)
    assert calls[0][1] == {"region_name": "eu-west-1"}


def test_upload_payload_serializes_json_body():
    s3_client = FakeS3Client()

    ingest.upload_payload(
        s3_client=s3_client,
        bucket="raw-bucket",
        object_key="traffic/file.json",
        payload={"total_records": 1},
    )

    call = s3_client.put_object_calls[0]
    assert call["Bucket"] == "raw-bucket"
    assert call["Key"] == "traffic/file.json"
    assert call["ContentType"] == "application/json"
    assert json.loads(call["Body"].decode("utf-8")) == {"total_records": 1}
