import logging
import os
import sys
from datetime import date, timedelta


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def _parse_cli_args(argv: list[str]) -> dict[str, str]:
    args = {}
    index = 1
    while index < len(argv):
        token = argv[index]
        if token.startswith("--") and index + 1 < len(argv):
            args[token[2:]] = argv[index + 1]
            index += 2
        else:
            index += 1
    return args


def get_job_args(argv: list[str]) -> dict[str, str]:
    default_ingest_date = (date.today() - timedelta(days=1)).isoformat()
    cli_args = _parse_cli_args(argv)
    resolved = {}

    glue_keys = [
        key
        for key in (
            "JOB_NAME",
            "SOURCE_NAME",
            "RAW_BUCKET",
            "CURATED_BUCKET",
            "INGEST_DATE",
            "INPUT_PATH",
            "OUTPUT_PATH",
            "WRITE_MODE",
        )
        if f"--{key}" in argv
    ]
    if glue_keys:
        try:
            from awsglue.utils import getResolvedOptions

            resolved.update(getResolvedOptions(argv, glue_keys))
        except ModuleNotFoundError:
            resolved.update({key: cli_args[key] for key in glue_keys if key in cli_args})

    resolved.update(cli_args)
    source_name = resolved.get("SOURCE_NAME") or resolved.get("SOURCE") or os.environ.get("SOURCE_NAME") or os.environ.get("INGEST_SOURCE")
    raw_bucket = resolved.get("RAW_BUCKET") or os.environ.get("RAW_BUCKET")
    curated_bucket = resolved.get("CURATED_BUCKET") or os.environ.get("CURATED_BUCKET")

    if not source_name:
        raise ValueError("SOURCE_NAME is required")
    source_name = source_name.strip().lower()
    if not raw_bucket and not resolved.get("INPUT_PATH"):
        raise ValueError("RAW_BUCKET is required unless INPUT_PATH is provided")
    if not curated_bucket and not resolved.get("OUTPUT_PATH"):
        raise ValueError("CURATED_BUCKET is required unless OUTPUT_PATH is provided")

    return {
        "job_name": resolved.get("JOB_NAME") or os.environ.get("JOB_NAME") or f"transform-{source_name}",
        "source_name": source_name,
        "raw_bucket": raw_bucket or "",
        "curated_bucket": curated_bucket or "",
        "ingest_date": resolved.get("INGEST_DATE") or os.environ.get("INGEST_DATE") or default_ingest_date,
        "input_path": resolved.get("INPUT_PATH") or os.environ.get("INPUT_PATH") or "",
        "output_path": resolved.get("OUTPUT_PATH") or os.environ.get("OUTPUT_PATH") or "",
        "write_mode": resolved.get("WRITE_MODE") or os.environ.get("WRITE_MODE") or "append",
    }


def s3_path(bucket_or_uri: str, *parts: str) -> str:
    base = bucket_or_uri.rstrip("/")
    if not base.startswith("s3://"):
        base = f"s3://{base}"
    suffix = "/".join(part.strip("/") for part in parts if part)
    return f"{base}/{suffix}" if suffix else base


def build_input_path(args: dict[str, str]) -> str:
    if args["input_path"]:
        return args["input_path"]
    ingest_day = date.fromisoformat(args["ingest_date"])
    return s3_path(
        args["raw_bucket"],
        args["source_name"],
        f"year={ingest_day.year:04d}",
        f"month={ingest_day.month:02d}",
        f"day={ingest_day.day:02d}",
    )


def build_output_path(args: dict[str, str]) -> str:
    if args["output_path"]:
        return args["output_path"]
    return s3_path(args["curated_bucket"], "curated", args["source_name"])


def main() -> None:
    from awsglue.context import GlueContext
    from awsglue.job import Job
    from pyspark.context import SparkContext
    from transformers import get_transformer

    args = get_job_args(sys.argv)
    transformer = get_transformer(args["source_name"], logger=logger)
    input_path = build_input_path(args)
    output_path = build_output_path(args)

    glue_context = GlueContext(SparkContext.getOrCreate())
    job = Job(glue_context)
    job.init(args["job_name"], args)
    spark = glue_context.spark_session

    logger.info("Reading %s raw JSON from %s", transformer.source_name, input_path)
    reader = spark.read.option("multiLine", "true")
    schema = transformer.raw_schema()
    if schema is not None:
        reader = reader.schema(schema)
    raw_df = reader.json(input_path)
    curated_df = transformer.transform(raw_df)

    logger.info("Writing %s curated parquet to %s", transformer.source_name, output_path)
    (
        curated_df.write.mode(args["write_mode"])
        .partitionBy(*transformer.partition_cols())
        .parquet(output_path)
    )
    job.commit()
    logger.info("%s transform finished successfully", transformer.source_name.capitalize())


if __name__ == "__main__":
    main()
