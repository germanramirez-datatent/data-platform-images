import logging
import os
import sys
import time
from dataclasses import dataclass

import boto3
from botocore.exceptions import BotoCoreError, ClientError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


SUCCESS_STATES = {"SUCCEEDED"}
FAILURE_STATES = {"FAILED", "STOPPED", "TIMEOUT", "ERROR", "EXPIRED"}
DEFAULT_PROJECT_NAME = "data-platform"
DEFAULT_ENVIRONMENT = "dev"
DEFAULT_JOB_SUFFIX = "transform-to-curated"
DEFAULT_REGION = "eu-west-1"
DEFAULT_POLL_INTERVAL_SECONDS = 15
DEFAULT_TIMEOUT_SECONDS = 3600


@dataclass(frozen=True)
class GlueTriggerConfig:
    job_name: str
    source_name: str
    ingest_date: str
    region: str
    poll_interval_seconds: int
    timeout_seconds: int


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value or not value.strip():
        raise ValueError(f"{name} environment variable is required")
    return value.strip()


def _positive_int_env(name: str, default_value: int) -> int:
    raw_value = os.environ.get(name, str(default_value)).strip()
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer, got '{raw_value}'") from error

    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")

    return value


def _optional_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return ""


def resolve_job_name() -> str:
    explicit_job_name = _optional_env("GLUE_JOB_NAME")
    if explicit_job_name:
        return explicit_job_name

    project_name = _optional_env("PROJECT_NAME") or DEFAULT_PROJECT_NAME
    environment = _optional_env("ENVIRONMENT", "DEPLOY_ENV", "ENV") or DEFAULT_ENVIRONMENT
    job_suffix = _optional_env("GLUE_JOB_SUFFIX") or DEFAULT_JOB_SUFFIX
    return f"{project_name}-{environment}-{job_suffix}"


def get_config() -> GlueTriggerConfig:
    source_name = os.environ.get("SOURCE_NAME") or os.environ.get("INGEST_SOURCE")
    if not source_name or not source_name.strip():
        raise ValueError("SOURCE_NAME environment variable is required")

    return GlueTriggerConfig(
        job_name=resolve_job_name(),
        source_name=source_name.strip().lower(),
        ingest_date=_required_env("INGEST_DATE"),
        region=(
            os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
            or DEFAULT_REGION
        ).strip(),
        poll_interval_seconds=_positive_int_env(
            "POLL_INTERVAL_SECONDS",
            DEFAULT_POLL_INTERVAL_SECONDS,
        ),
        timeout_seconds=_positive_int_env("GLUE_TRIGGER_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
    )


def start_glue_job(glue_client, config: GlueTriggerConfig) -> str:
    logger.info(
        "Starting Glue job job_name=%s source_name=%s ingest_date=%s region=%s",
        config.job_name,
        config.source_name,
        config.ingest_date,
        config.region,
    )
    response = glue_client.start_job_run(
        JobName=config.job_name,
        Arguments={
            "--SOURCE_NAME": config.source_name,
            "--INGEST_DATE": config.ingest_date,
        },
    )
    job_run_id = response["JobRunId"]
    logger.info("Glue job started job_name=%s job_run_id=%s", config.job_name, job_run_id)
    return job_run_id


def _log_terminal_failure(job_run: dict) -> None:
    error_message = job_run.get("ErrorMessage")
    state_detail = job_run.get("StateDetail")

    if error_message:
        logger.error("Glue job error_message=%s", error_message)
    if state_detail:
        logger.error("Glue job state_detail=%s", state_detail)


def wait_for_glue_job(glue_client, config: GlueTriggerConfig, job_run_id: str) -> str:
    started_at = time.monotonic()
    deadline = started_at + config.timeout_seconds

    while True:
        response = glue_client.get_job_run(
            JobName=config.job_name,
            RunId=job_run_id,
        )
        job_run = response["JobRun"]
        state = job_run["JobRunState"]
        elapsed_seconds = int(time.monotonic() - started_at)

        logger.info(
            "Glue job status job_name=%s job_run_id=%s state=%s elapsed_seconds=%s",
            config.job_name,
            job_run_id,
            state,
            elapsed_seconds,
        )

        if state in SUCCESS_STATES:
            logger.info("Glue job finished successfully job_run_id=%s", job_run_id)
            return state

        if state in FAILURE_STATES:
            _log_terminal_failure(job_run)
            raise RuntimeError(f"Glue job {job_run_id} finished with state {state}")

        if time.monotonic() >= deadline:
            logger.error(
                "Glue job timed out job_run_id=%s timeout_seconds=%s",
                job_run_id,
                config.timeout_seconds,
            )
            glue_client.stop_job_run(JobName=config.job_name, RunId=job_run_id)
            raise TimeoutError(f"Glue job {job_run_id} exceeded timeout")

        time.sleep(config.poll_interval_seconds)


def run() -> None:
    config = get_config()
    glue_client = boto3.client("glue", region_name=config.region)
    job_run_id = start_glue_job(glue_client, config)
    wait_for_glue_job(glue_client, config, job_run_id)


def main() -> None:
    try:
        run()
    except (ValueError, RuntimeError, TimeoutError) as error:
        logger.error("Glue trigger failed: %s", error)
        sys.exit(1)
    except (BotoCoreError, ClientError):
        logger.exception("Glue trigger failed because AWS returned an error")
        sys.exit(1)
    except Exception:
        logger.exception("Glue trigger failed unexpectedly")
        sys.exit(1)


if __name__ == "__main__":
    main()
