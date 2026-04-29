import logging
from abc import ABC, abstractmethod

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StructType


class BaseTransformer(ABC):
    source_name = ""
    event_date_column = "event_date"

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)

    @abstractmethod
    def transform(self, df: DataFrame) -> DataFrame:
        """Receive a raw JSON DataFrame and return a typed curated DataFrame."""
        raise NotImplementedError

    def raw_schema(self) -> StructType | None:
        return None

    def explode_struct_array(
        self,
        df: DataFrame,
        array_col: str,
        alias: str = "record",
        include_cols: tuple[str, ...] = (),
    ) -> DataFrame:
        exploded = self.explode_array(df, array_col, alias=alias, include_cols=include_cols)
        return exploded.select(f"{alias}.*", *include_cols)

    def explode_array(
        self,
        df: DataFrame,
        array_col: str,
        alias: str,
        include_cols: tuple[str, ...] = (),
    ) -> DataFrame:
        return df.select(
            F.explode(F.col(array_col)).alias(alias),
            *(F.col(column_name) for column_name in include_cols),
        )

    def explode_zipped_arrays(
        self,
        df: DataFrame,
        array_cols: tuple[str, ...],
        alias: str = "record",
        include_cols: tuple[str, ...] = (),
    ) -> DataFrame:
        zipped_cols = [
            F.col(column_name).alias(column_name.rsplit(".", maxsplit=1)[-1])
            for column_name in array_cols
        ]
        exploded = df.select(
            F.explode(F.arrays_zip(*zipped_cols)).alias(alias),
            *(F.col(column_name) for column_name in include_cols),
        )
        return exploded.select(f"{alias}.*", *include_cols)

    def partition_cols(self) -> list[str]:
        return ["year", "month", "day"]

    def add_event_partitions(self, df: DataFrame, event_date_col: str | None = None) -> DataFrame:
        column_name = event_date_col or self.event_date_column
        return (
            df.withColumn("year", F.year(F.col(column_name)))
            .withColumn("month", F.month(F.col(column_name)))
            .withColumn("day", F.dayofmonth(F.col(column_name)))
        )
