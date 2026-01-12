"""Category code value object for transaction categorization."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class CategoryCode(BaseModel):
    """Value object for transaction category identification."""

    code: str
    name: str
    parent_code: Optional[str] = None

    model_config = ConfigDict(
        frozen=True,  # Immutable
        str_strip_whitespace=True,  # Auto-strip whitespace
    )

    def __init__(
        self,
        code: str | None = None,
        name: str | None = None,
        parent_code: Optional[str] = None,
        **data: Any,
    ):
        """
        Initialize CategoryCode with positional or keyword arguments.

        Supports both CategoryCode("FOOD", "Groceries") and
        CategoryCode(code="FOOD", name="Groceries").
        """
        # Only pass values that weren't passed as keyword arguments in data
        if "code" not in data:
            data["code"] = code
        if "name" not in data:
            data["name"] = name
        if "parent_code" not in data:
            data["parent_code"] = parent_code
        super().__init__(**data)

    @field_validator("code", "name")
    @classmethod
    def validate_not_empty(cls, v: Any, info) -> str:
        """Validate that code and name are not empty."""
        field_name = info.field_name.replace("_", " ").title()

        if not v or len(str(v).strip()) == 0:
            msg = f"Category {field_name.lower()} cannot be empty"
            raise ValueError(msg)

        # Normalize: code to uppercase, name by trimming
        if info.field_name == "code":
            return str(v).upper().strip()
        return str(v).strip()

    @field_validator("parent_code")
    @classmethod
    def normalize_parent_code(cls, v: Optional[str]) -> Optional[str]:
        """Normalize parent code or convert empty to None."""
        if v is None:
            return None

        normalized = str(v).upper().strip()
        # Convert empty string to None
        return normalized if len(normalized) > 0 else None

    def is_subcategory(self) -> bool:
        """Check if this is a subcategory."""
        return self.parent_code is not None and len(self.parent_code) > 0

    def __str__(self) -> str:
        """String representation of category."""
        if self.is_subcategory():
            return f"{self.parent_code}.{self.code} - {self.name}"
        return f"{self.code} - {self.name}"
