from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, BooleanType, IntegerType, StringType, StructField, StructType

from transformers.base import BaseTransformer


class HolidaysTransformer(BaseTransformer):
    source_name = "holidays"

    def raw_schema(self) -> StructType:
        holiday_schema = StructType(
            [
                StructField("date", StringType(), True),
                StructField("localName", StringType(), True),
                StructField("name", StringType(), True),
                StructField("countryCode", StringType(), True),
                StructField("fixed", BooleanType(), True),
                StructField("global", BooleanType(), True),
                StructField("counties", ArrayType(StringType()), True),
                StructField("launchYear", IntegerType(), True),
                StructField("types", ArrayType(StringType()), True),
            ]
        )
        return StructType(
            [
                StructField("source", StringType(), True),
                StructField("country_code", StringType(), True),
                StructField("ingest_date", StringType(), True),
                StructField("total_records", IntegerType(), True),
                StructField("holidays", ArrayType(holiday_schema), True),
            ]
        )

    def transform(self, df: DataFrame) -> DataFrame:
        records = self.explode_struct_array(
            df,
            "holidays",
            alias="holiday",
            include_cols=("country_code", "ingest_date"),
        )
        curated = records.select(
            F.coalesce(F.to_date("date"), F.to_date("ingest_date")).alias("event_date"),
            F.col("country_code").cast("string").alias("country_code"),
            F.col("localName").cast("string").alias("local_name"),
            F.col("name").cast("string").alias("name"),
            F.col("fixed").cast("boolean").alias("is_fixed"),
            F.col("global").cast("boolean").alias("is_global"),
            F.col("launchYear").cast("int").alias("launch_year"),
            F.col("types").alias("holiday_types"),
            F.to_date("ingest_date").alias("ingest_date"),
        )
        curated = curated.dropDuplicates(["event_date", "country_code", "name"])
        return self.add_event_partitions(curated)
