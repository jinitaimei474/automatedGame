from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ParameterType = Literal["integer", "number", "boolean", "string", "select"]


class ParameterValidationError(ValueError):
    """An error suitable for displaying directly in the Chinese UI."""


@dataclass(frozen=True)
class TaskParameter:
    key: str
    label: str
    type: ParameterType
    required: bool = False
    default_value: Any = None
    min: float | None = None
    max: float | None = None
    description: str = ""
    unit: str = ""
    options: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "type": self.type,
            "required": self.required,
            "defaultValue": self.default_value,
            "min": self.min,
            "max": self.max,
            "description": self.description,
            "unit": self.unit,
            "options": list(self.options),
        }


def validate_parameters(schema: tuple[TaskParameter, ...], values: dict[str, Any]) -> dict[str, Any]:
    validated: dict[str, Any] = {}
    for item in schema:
        value = values.get(item.key, item.default_value)
        if item.required and (value is None or value == ""):
            raise ParameterValidationError(f"请输入{item.label}")
        if item.type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ParameterValidationError(f"{item.label}必须是正整数")
        elif item.type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ParameterValidationError(f"{item.label}必须是数字")
        elif item.type == "boolean" and not isinstance(value, bool):
            raise ParameterValidationError(f"{item.label}必须是布尔值")
        elif item.type == "string" and not isinstance(value, str):
            raise ParameterValidationError(f"{item.label}必须是文本")
        elif item.type == "select" and value not in item.options:
            raise ParameterValidationError(f"请选择有效的{item.label}")
        if item.min is not None and isinstance(value, (int, float)) and value < item.min:
            raise ParameterValidationError(f"{item.label}不能小于{item.min:g}")
        if item.max is not None and isinstance(value, (int, float)) and value > item.max:
            raise ParameterValidationError(f"{item.label}不能超过{item.max:g}")
        validated[item.key] = value
    return validated

