from __future__ import annotations

from enum import Enum
from typing import Any, Dict, get_type_hints


class _UnsetType:
    pass


_UNSET = _UnsetType()


class FieldInfo:
    def __init__(self, default: Any = _UNSET, *, default_factory=None, **_: Any) -> None:
        self.default = default
        self.default_factory = default_factory


def Field(default: Any = _UNSET, *, default_factory=None, **kwargs: Any) -> FieldInfo:
    return FieldInfo(default=default, default_factory=default_factory, **kwargs)


class BaseModelMeta(type):
    def __new__(mcls, name, bases, namespace):
        cls = super().__new__(mcls, name, bases, dict(namespace))
        resolved_types = {
            name: hint
            for name, hint in get_type_hints(cls).items()
            if not name.startswith("__")
        }
        defaults: Dict[str, Any] = {}
        for field_name in resolved_types:
            value = namespace.get(field_name, _UNSET)
            if isinstance(value, FieldInfo) or value is not _UNSET:
                defaults[field_name] = value
        cls.__field_types__ = resolved_types
        cls.__field_defaults__ = defaults
        return cls


class BaseModel(metaclass=BaseModelMeta):
    __field_types__: Dict[str, Any]
    __field_defaults__: Dict[str, Any]

    def __init__(self, **data: Any) -> None:
        for field_name, annotation in self.__field_types__.items():
            if field_name in data:
                value = data[field_name]
            elif field_name in self.__field_defaults__:
                default = self.__field_defaults__[field_name]
                if isinstance(default, FieldInfo) and default.default_factory is not None:
                    value = default.default_factory()
                elif isinstance(default, FieldInfo) and default.default is not _UNSET:
                    value = default.default
                else:
                    value = default
            else:
                raise ValueError(f"Missing field {field_name}")
            value = self._convert_field(annotation, value)
            setattr(self, field_name, value)
        for key, value in data.items():
            if key not in self.__field_types__:
                setattr(self, key, value)

    @classmethod
    def _convert_field(cls, annotation: Any, value: Any) -> Any:
        origin = getattr(annotation, "__origin__", None)
        args = getattr(annotation, "__args__", ())
        if isinstance(value, dict) and isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return annotation(**value)
        if origin is list and args:
            subtype = args[0]
            return [cls._convert_field(subtype, item) for item in value]
        if origin is dict and args:
            value_type = args[1] if len(args) > 1 else Any
            return {k: cls._convert_field(value_type, v) for k, v in value.items()}
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return annotation(value)
        return value

    def model_dump(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for field_name in self.__field_types__:
            value = getattr(self, field_name)
            result[field_name] = self._serialize_value(value)
        return result

    @classmethod
    def _serialize_value(cls, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump()
        if isinstance(value, list):
            return [cls._serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {k: cls._serialize_value(v) for k, v in value.items()}
        return value

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        return cls(**data)


__all__ = ["BaseModel", "Field"]

