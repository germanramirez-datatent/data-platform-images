from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from transformers.base import BaseTransformer


class TrafficTransformer(BaseTransformer):
    source_name = "traffic"

    def transform(self, df: DataFrame) -> DataFrame:
        records = self.explode_struct_array(df, "records")
        curated = records.select(
            F.col("center_id").cast("string").alias("center_id"),
            F.to_timestamp("timestamp").alias("event_timestamp"),
            F.to_date("timestamp").alias("event_date"),
            F.col("visitors_count").cast("int").alias("visitors_count"),
            F.col("day_of_week").cast("string").alias("day_of_week"),
            F.col("is_holiday").cast("boolean").alias("is_holiday"),
            F.col("weather_condition").cast("string").alias("weather_condition"),
            F.col("temperature_c").cast("double").alias("temperature_c"),
        )
        curated = curated.dropDuplicates(["center_id", "event_timestamp"])
        return self.add_event_partitions(curated)
