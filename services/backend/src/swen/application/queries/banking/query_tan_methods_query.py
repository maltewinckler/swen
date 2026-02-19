"""Query TAN methods - discover available TAN methods from a bank."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from swen.domain.banking.ports import BankConnectionPort
from swen.domain.banking.value_objects import BankCredentials, TANMethod
from swen.infrastructure.banking.geldstrom_adapter import GeldstromAdapter

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


@dataclass
class TANMethodInfo:
    """Information about an available TAN method."""

    code: str
    name: str
    method_type: str
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
    def from_domain(cls, method: TANMethod) -> TANMethodInfo:
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


@dataclass
class TANMethodsResult:
    """Result of querying TAN methods from a bank."""

    blz: str
    bank_name: str
    tan_methods: list[TANMethodInfo]
    default_method: Optional[str] = None


class QueryTanMethodsQuery:
    """Query to discover available TAN methods from a bank."""

    def __init__(self, bank_adapter: BankConnectionPort):
        self._adapter = bank_adapter

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> QueryTanMethodsQuery:
        return cls(
            bank_adapter=GeldstromAdapter(
                config_repository=factory.fints_config_repository(),
            ),
        )

    async def execute(
        self,
        credentials: BankCredentials,
        bank_name: str,
    ) -> TANMethodsResult:
        tan_methods = await self._adapter.get_tan_methods(credentials)
        method_infos = [TANMethodInfo.from_domain(m) for m in tan_methods]
        default_method = None
        for method in method_infos:
            if method.is_decoupled:
                default_method = method.code
                break
        if not default_method and method_infos:
            default_method = method_infos[0].code

        return TANMethodsResult(
            blz=credentials.blz,
            bank_name=bank_name,
            tan_methods=method_infos,
            default_method=default_method,
        )
