from transformers.base import BaseTransformer
from transformers.flights import FlightsTransformer
from transformers.holidays import HolidaysTransformer
from transformers.traffic import TrafficTransformer
from transformers.weather import WeatherTransformer


TRANSFORMERS: dict[str, type[BaseTransformer]] = {
    TrafficTransformer.source_name: TrafficTransformer,
    WeatherTransformer.source_name: WeatherTransformer,
    HolidaysTransformer.source_name: HolidaysTransformer,
    FlightsTransformer.source_name: FlightsTransformer,
}


def get_transformer(source_name: str, logger=None) -> BaseTransformer:
    normalized_source = source_name.strip().lower()
    try:
        transformer_class = TRANSFORMERS[normalized_source]
    except KeyError as exc:
        supported_sources = ", ".join(sorted(TRANSFORMERS))
        raise ValueError(
            f"Unsupported SOURCE_NAME '{source_name}'. Supported values: {supported_sources}"
        ) from exc

    return transformer_class(logger=logger)
