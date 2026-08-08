"""Adapter factory protocol for swen_identity's application layer."""

from __future__ import annotations

from typing import Protocol

from swen_identity.domain.ports import PasswordHashingPort, TokenHandlingPort


class AdapterFactory(Protocol):
    """Protocol for creating swen_identity infrastructure adapters."""

    def token_handling_port(self) -> TokenHandlingPort:
        """Get the token handling adapter."""
        ...

    def password_hashing_port(self) -> PasswordHashingPort:
        """Get the password hashing adapter."""
        ...
