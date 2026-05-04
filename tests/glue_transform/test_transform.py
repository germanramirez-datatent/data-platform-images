import importlib
import sys
import types

import pytest


def test_get_job_args_accepts_cli_values(monkeypatch):
    monkeypatch.delenv("SOURCE_NAME", raising=False)
    monkeypatch.delenv("RAW_BUCKET", raising=False)
    monkeypatch.delenv("CURATED_BUCKET", raising=False)
    transform = importlib.import_module("transform")

    args = transform.get_job_args(
        [
            "transform.py",
            "--SOURCE_NAME",
            "traffic",
            "--RAW_BUCKET",
            "raw-bucket",
            "--CURATED_BUCKET",
            "curated-bucket",
            "--INGEST_DATE",
            "2026-04-22",
        ]
    )

    assert args["source_name"] == "traffic"
    assert args["raw_bucket"] == "raw-bucket"
    assert args["curated_bucket"] == "curated-bucket"
    assert args["ingest_date"] == "2026-04-22"
    assert args["write_mode"] == "append"


def test_build_paths_use_source_and_ingest_date():
    transform = importlib.import_module("transform")
    args = {
        "source_name": "weather",
        "raw_bucket": "data-platform-dev-raw",
        "curated_bucket": "s3://data-platform-dev-curated",
        "ingest_date": "2026-04-22",
        "input_path": "",
        "output_path": "",
    }

    assert transform.build_input_path(args) == (
        "s3://data-platform-dev-raw/weather/year=2026/month=04/day=22"
    )
    assert transform.build_output_path(args) == "s3://data-platform-dev-curated/curated/weather"


def test_build_catalog_table_name_quotes_identifier_parts():
    transform = importlib.import_module("transform")

    assert (
        transform.build_catalog_table_name("data-platform_dev_curated", "traffic")
        == "`data-platform_dev_curated`.`traffic`"
    )


def test_get_job_args_requires_input_and_output_locations(monkeypatch):
    monkeypatch.delenv("RAW_BUCKET", raising=False)
    monkeypatch.delenv("CURATED_BUCKET", raising=False)
    transform = importlib.import_module("transform")

    with pytest.raises(ValueError, match="RAW_BUCKET"):
        transform.get_job_args(["transform.py", "--SOURCE_NAME", "traffic"])


def test_get_transformer_selects_source_strategy(monkeypatch):
    pyspark_module = types.ModuleType("pyspark")
    sql_module = types.ModuleType("pyspark.sql")
    functions_module = types.ModuleType("pyspark.sql.functions")
    types_module = types.ModuleType("pyspark.sql.types")
    sql_module.DataFrame = object
    sql_module.functions = functions_module
    for type_name in (
        "ArrayType",
        "BooleanType",
        "IntegerType",
        "StringType",
        "StructField",
        "StructType",
    ):
        setattr(types_module, type_name, object)
    monkeypatch.setitem(sys.modules, "pyspark", pyspark_module)
    monkeypatch.setitem(sys.modules, "pyspark.sql", sql_module)
    monkeypatch.setitem(sys.modules, "pyspark.sql.functions", functions_module)
    monkeypatch.setitem(sys.modules, "pyspark.sql.types", types_module)
    monkeypatch.delitem(sys.modules, "transformers", raising=False)

    transformers = importlib.import_module("transformers")

    assert transformers.get_transformer(" FLIGHTS ").source_name == "flights"
    with pytest.raises(ValueError, match="Unsupported SOURCE_NAME"):
        transformers.get_transformer("unknown")
