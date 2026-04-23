import logging
import os
from abc import ABC, abstractmethod
from datetime import date


class BaseAdapter(ABC):
    source_name = ""
    required_env: tuple[str, ...] = ()

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)
        self.validate_required_env()

    def validate_required_env(self) -> None:
        missing_variables = [name for name in self.required_env if not os.environ.get(name)]
        if missing_variables:
            missing_list = ", ".join(sorted(missing_variables))
            raise ValueError(f"Missing required environment variables for {self.source_name}: {missing_list}")

    @abstractmethod
    def fetch_payload(self, ingest_day: date) -> dict:
        raise NotImplementedError

    @abstractmethod
    def build_object_key(self, ingest_day: date) -> str:
        raise NotImplementedError
