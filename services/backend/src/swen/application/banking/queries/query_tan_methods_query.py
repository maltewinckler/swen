"""Query TAN methods - discover available TAN methods from a bank."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.banking.dtos import TANMethodInfoDTO, TANMethodsResultDTO
from swen.domain.banking.exceptions import CredentialsNotFoundError
from swen.infrastructure.banking.bank_connection_dispatcher import (
    BankConnectionDispatcher,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.banking.ports import BankConnectionPort
    from swen.domain.banking.repositories import BankCredentialRepository


class QueryTanMethodsQuery:
    """Query to discover available TAN methods from a bank."""

    def __init__(
        self,
        bank_adapter: BankConnectionPort,
        credential_repo: BankCredentialRepository,
    ):
        self._adapter = bank_adapter
        self._credential_repo = credential_repo

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> QueryTanMethodsQuery:
        return cls(
            bank_adapter=BankConnectionDispatcher.from_factory(factory),
            credential_repo=factory.credential_repository(),
        )

    async def execute(
        self,
        blz: str,
        bank_name: str,
    ) -> TANMethodsResultDTO:
        credentials = await self._credential_repo.find_by_blz(blz)
        if credentials is None:
            raise CredentialsNotFoundError(blz=blz)

        tan_methods = await self._adapter.get_tan_methods(credentials)
        method_infos = [TANMethodInfoDTO.from_domain(m) for m in tan_methods]
        default_method = None
        for method in method_infos:
            if method.is_decoupled:
                default_method = method.code
                break
        if not default_method and method_infos:
            default_method = method_infos[0].code

        return TANMethodsResultDTO(
            blz=blz,
            bank_name=bank_name,
            tan_methods=method_infos,
            default_method=default_method,
        )
