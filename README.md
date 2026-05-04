# Data Platform Images

Containerized runtime code for the shopping center data platform. This repository contains the services and jobs used by Argo workflows to simulate traffic, ingest source data, validate raw payloads, trigger AWS Glue, and transform raw JSON into curated Parquet.

## Components

| Component | Path | Purpose |
| --- | --- | --- |
| Simulation API | `simulation-api` | FastAPI service that generates hourly shopping center traffic records. |
| Python ingestor | `python-ingestor` | Fetches traffic, weather, holiday, or flight payloads and writes them to S3-compatible storage. |
| Data quality | `data-quality` | Downloads a raw payload and validates expected record counts. |
| Glue trigger | `glue-trigger` | Starts the AWS Glue transform job for a source and waits for completion. |
| Glue transform | `glue-transform` | PySpark transformation package used by AWS Glue to write curated Parquet tables. |

Supported ingestion sources:

- `traffic`: simulated hourly traffic from the local simulation API.
- `weather`: hourly weather observations from Open-Meteo.
- `holidays`: Spanish public holidays from Nager.Date.
- `flights`: aircraft snapshots from OpenSky Network.

## Repository Layout

```text
.
|-- data-quality
|-- glue-trigger
|-- glue-transform
|-- python-ingestor
|-- simulation-api
`-- tests
```

## Build Images

Build the local images expected by the Argo workflows:

```bash
docker build -t simulation-api:local simulation-api
docker build -t python-ingestor:local python-ingestor
docker build -t data-quality:local data-quality
docker build -t glue-trigger:local glue-trigger
```

The Glue transform code is packaged as a Python wheel and uploaded to the infrastructure assets bucket for Glue:

```bash
cd glue-transform
python setup.py bdist_wheel
```

The Terraform Glue job expects:

```text
s3://<assets-bucket>/glue/transform.py
s3://<assets-bucket>/glue/glue_transformers-0.1.0-py3-none-any.whl
```

## Simulation API

Run locally:

```bash
cd simulation-api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Endpoints:

- `GET /health`
- `GET /traffic/current?center_id=EUR_MAD_001`
- `GET /traffic/historical?center_id=EUR_MAD_001&date=2026-04-22`
- `GET /traffic/range?center_id=EUR_MAD_001&from=2026-04-22&to=2026-04-22`

The generator applies hourly, weekday, monthly, weather, holiday, and random-noise factors to produce realistic traffic variation.

## Python Ingestor

Run an ingestion job with:

```bash
cd python-ingestor
pip install -r requirements.txt
python ingest.py
```

Common environment variables:

| Variable | Required | Purpose |
| --- | --- | --- |
| `INGEST_SOURCE` | No | Source to ingest. Defaults to `traffic`. |
| `INGEST_DATE` | No | Date to ingest. Defaults to yesterday. |
| `RAW_BUCKET` | Yes | Destination S3 or MinIO bucket. |
| `MINIO_ENDPOINT` | No | S3-compatible endpoint for local MinIO. Empty means AWS S3. |
| `AWS_ACCESS_KEY_ID` | Depends | Access key for S3 or MinIO. |
| `AWS_SECRET_ACCESS_KEY` | Depends | Secret key for S3 or MinIO. |

Source-specific variables:

| Source | Variables |
| --- | --- |
| `traffic` | `SIMULATION_API_URL`, `CENTER_ID` |
| `weather` | `WEATHER_LATITUDE`, `WEATHER_LONGITUDE`, optional `OPEN_METEO_URL`, `WEATHER_TIMEZONE` |
| `holidays` | `HOLIDAYS_COUNTRY_CODE`, optional `NAGER_DATE_URL` |
| `flights` | `OPENSKY_CLIENT_ID`, `OPENSKY_CLIENT_SECRET`, `OPENSKY_LAMIN`, `OPENSKY_LAMAX`, `OPENSKY_LOMIN`, `OPENSKY_LOMAX`, optional OpenSky URL overrides |

Raw object keys are partitioned by source and date:

```text
<source>/year=YYYY/month=MM/day=DD/<file>.json
```

## Data Quality

Run a payload validation job with:

```bash
cd data-quality
pip install -r requirements.txt
python validate.py
```

Required variables:

- `BUCKET`
- `OBJECT_KEY`
- `EXPECTED_RECORDS`

Optional variables:

- `MINIO_ENDPOINT`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `VALIDATION_FIELD_PATH`, default `total_records`
- `VALIDATION_MODE`, one of `value`, `count`, or `gte`

Examples:

- Traffic validates `records` with `count`.
- Weather validates `hourly.time` with `count`.
- Flights validates `states` with `gte`.

## Glue Trigger

The Glue trigger starts a Glue job and polls until it reaches a terminal state.

Required variables:

- `SOURCE_NAME`
- `INGEST_DATE`

Useful optional variables:

- `GLUE_JOB_NAME`
- `PROJECT_NAME`, default `data-platform`
- `ENVIRONMENT`, default `dev`
- `AWS_REGION`, default `eu-west-1`
- `POLL_INTERVAL_SECONDS`, default `15`
- `GLUE_TRIGGER_TIMEOUT_SECONDS`, default `3600`

When `GLUE_JOB_NAME` is not provided, the job name is resolved as:

```text
<PROJECT_NAME>-<ENVIRONMENT>-transform-to-curated
```

## Glue Transform

The Glue transform job reads raw JSON for a source and writes curated Parquet partitioned by `year`, `month`, and `day`.

Supported transformers:

- `traffic`: explodes traffic records, casts typed fields, and deduplicates by center and timestamp.
- `weather`: zips hourly weather arrays into hourly observation rows.
- `holidays`: explodes matching public holiday records and applies a typed schema.
- `flights`: explodes OpenSky state arrays into typed aircraft snapshot rows.

The job can receive Glue-style CLI arguments such as:

```bash
--SOURCE_NAME traffic
--RAW_BUCKET data-platform-dev-raw-
--CURATED_BUCKET data-platform-dev-curated-
--INGEST_DATE 2026-04-22
--WRITE_MODE overwrite
--CURATED_DATABASE data_platform_dev_curated
```

## Tests

Install test dependencies and run the suite:

```bash
pip install -r requirements-dev.txt
pytest
```

The tests cover adapters, simulation logic, validation behavior, and Glue transform helpers.
