"""DTOs for TAN method discovery."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

from swen.domain.banking.value_objects import TANMethod

# Mirrors TANMethodType's values as a plain string Literal, kept in sync manually.
# Not a domain concept itself -- exists only so this DTO (and the presentation
# schema that inherits from it) can flatten the enum to str while keeping
# strict typing for OpenAPI's generated enum documentation.
TANMethodTypeStr = Literal[
    "decoupled",
    "push",
    "sms",
    "chiptan",
    "photo_tan",
    "manual",
    "unknown",
]


class TANMethodInfoDTO(BaseModel):
    """Information about an available TAN method."""

    model_config = ConfigDict(frozen=True)

    code: str
    name: str
    method_type: TANMethodTypeStr
    is_decoupled: bool
    technical_id: Optional[str] = None
    zka_id: Optional[str] = None
    zka_version: Optional[str] = None
    max_tan_length: Optional[int] = None
    decoupled_max_polls: Optional[int] = None
    decoupled_first_poll_delay: Optional[int] = None
    decoupled_poll_interval: Optional[int] = None
    supports_cancel: bool = False
    supports_multiple_tan: bool = False

    @classmethod
    def from_domain(cls, method: TANMethod) -> TANMethodInfoDTO:
        return cls(
            code=method.code,
            name=method.name,
            method_type=method.method_type.value,
            is_decoupled=method.is_decoupled,
            technical_id=method.technical_id,
            zka_id=method.zka_id,
            zka_version=method.zka_version,
            max_tan_length=method.max_tan_length,
            decoupled_max_polls=method.decoupled_max_polls,
            decoupled_first_poll_delay=method.decoupled_first_poll_delay,
            decoupled_poll_interval=method.decoupled_poll_interval,
            supports_cancel=method.supports_cancel,
            supports_multiple_tan=method.supports_multiple_tan,
        )


class TANMethodsResultDTO(BaseModel):
    """Result of querying TAN methods from a bank."""

    model_config = ConfigDict(frozen=True)

    blz: str
    bank_name: str
    tan_methods: list[TANMethodInfoDTO]
    default_method: Optional[str] = None
