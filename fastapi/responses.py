from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from uuid import UUID
from typing import Any, Dict, Iterable


class Response:
    def __init__(self, *, status_code: int, body: Any) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> Any:
        return self._body


def serialize(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        # Ensure nested fields (e.g., UUID, datetime) are also serialized
        return serialize(value.model_dump())
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: serialize(val) for key, val in value.items()}
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, tuple):
        return [serialize(item) for item in value]
    return value


__all__ = ["Response", "serialize"]

