from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from transformers.base import BaseTransformer


class FlightsTransformer(BaseTransformer):
    source_name = "flights"

    def transform(self, df: DataFrame) -> DataFrame:
        records = self.explode_array(
            df,
            "states",
            alias="state",
            include_cols=("ingest_date", "snapshot_time", "time"),
        )
        curated = records.select(
            F.col("state").getItem(0).cast("string").alias("icao24"),
            F.trim(F.col("state").getItem(1)).cast("string").alias("callsign"),
            F.col("state").getItem(2).cast("string").alias("origin_country"),
            F.col("state").getItem(3).cast("long").alias("time_position"),
            F.col("state").getItem(4).cast("long").alias("last_contact"),
            F.col("state").getItem(5).cast("double").alias("longitude"),
            F.col("state").getItem(6).cast("double").alias("latitude"),
            F.col("state").getItem(7).cast("double").alias("baro_altitude"),
            F.col("state").getItem(8).cast("boolean").alias("on_ground"),
            F.col("state").getItem(9).cast("double").alias("velocity"),
            F.col("state").getItem(10).cast("double").alias("true_track"),
            F.col("state").getItem(11).cast("double").alias("vertical_rate"),
            F.col("state").getItem(13).cast("double").alias("geo_altitude"),
            F.col("state").getItem(14).cast("string").alias("squawk"),
            F.col("state").getItem(15).cast("boolean").alias("spi"),
            F.col("state").getItem(16).cast("int").alias("position_source"),
            F.col("snapshot_time").cast("long").alias("snapshot_time"),
            F.col("time").cast("long").alias("source_time"),
            F.to_date("ingest_date").alias("event_date"),
        )
        curated = curated.dropDuplicates(["icao24", "snapshot_time"])
        return self.add_event_partitions(curated)
