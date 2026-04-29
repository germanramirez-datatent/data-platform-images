from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from transformers.base import BaseTransformer


class WeatherTransformer(BaseTransformer):
    source_name = "weather"

    def transform(self, df: DataFrame) -> DataFrame:
        records = self.explode_zipped_arrays(
            df,
            (
                "hourly.time",
                "hourly.temperature_2m",
                "hourly.precipitation",
                "hourly.windspeed_10m",
                "hourly.weathercode",
            ),
            include_cols=("latitude", "longitude", "timezone"),
        )
        curated = records.select(
            F.to_timestamp("time").alias("event_timestamp"),
            F.to_date("time").alias("event_date"),
            F.col("temperature_2m").cast("double").alias("temperature_c"),
            F.col("precipitation").cast("double").alias("precipitation_mm"),
            F.col("windspeed_10m").cast("double").alias("wind_speed_kmh"),
            F.col("weathercode").cast("int").alias("weather_code"),
            F.col("latitude").cast("double").alias("latitude"),
            F.col("longitude").cast("double").alias("longitude"),
            F.col("timezone").cast("string").alias("timezone")
        )
        curated = curated.dropDuplicates(["event_timestamp", "latitude", "longitude"])
        return self.add_event_partitions(curated)
