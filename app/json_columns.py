"""SQLAlchemy JSON TypeDecorator for nested Pydantic/SQLModel schemas."""

from typing import Any

from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator
from sqlmodel import SQLModel


class PydanticJSON(TypeDecorator):
    """Persist a Pydantic/SQLModel instance as a JSON column."""

    impl = JSON
    cache_ok = True

    def __init__(self, pydantic_model: type[SQLModel]) -> None:
        """Bind the decorator to a nested schema class."""
        super().__init__()
        self.pydantic_model = pydantic_model

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        """Dump nested models to JSON-compatible dicts."""
        if value is None:
            return None
        if isinstance(value, self.pydantic_model):
            return value.model_dump(mode="json")
        return self.pydantic_model.model_validate(value).model_dump(mode="json")

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        """Rehydrate nested models from JSON."""
        if value is None:
            return None
        return self.pydantic_model.model_validate(value)
