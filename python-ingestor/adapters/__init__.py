from base_adapter import BaseAdapter

from .flights import FlightsAdapter
from .holidays import HolidaysAdapter
from .traffic import TrafficAdapter
from .weather import WeatherAdapter


ADAPTERS: dict[str, type[BaseAdapter]] = {
    TrafficAdapter.source_name: TrafficAdapter,
    WeatherAdapter.source_name: WeatherAdapter,
    HolidaysAdapter.source_name: HolidaysAdapter,
    FlightsAdapter.source_name: FlightsAdapter,
}


def get_adapter(source_name: str, logger=None) -> BaseAdapter:
    normalized_source = source_name.strip().lower()
    try:
        adapter_class = ADAPTERS[normalized_source]
    except KeyError as exc:
        supported_sources = ", ".join(sorted(ADAPTERS))
        raise ValueError(
            f"Unsupported INGEST_SOURCE '{source_name}'. Supported values: {supported_sources}"
        ) from exc

    return adapter_class(logger=logger)
