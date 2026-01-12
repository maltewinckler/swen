"""Import bank accounts and create accounting mappings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.dtos.accounting import BankAccountDTO
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency
from swen.domain.banking.value_objects import BankAccount
from swen.domain.integration.entities import AccountMapping
from swen.domain.shared.iban import normalize_iban

if TYPE_CHECKING:
    from swen.application.context import UserContext
    from swen.application.factories import RepositoryFactory
    from swen.domain.accounting.repositories import AccountRepository
    from swen.domain.integration.repositories import AccountMappingRepository


class BankAccountImportService:
    """Create asset accounts and IBAN mappings for imported bank accounts."""

    def __init__(
        self,
        account_repository: AccountRepository,
        mapping_repository: AccountMappingRepository,
        user_context: UserContext,
    ):
        self._account_repo = account_repository
        self._mapping_repo = mapping_repository
        self._user_id = user_context.user_id

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> BankAccountImportService:
        return cls(
            account_repository=factory.account_repository(),
            mapping_repository=factory.account_mapping_repository(),
            user_context=factory.user_context,
        )

    async def import_bank_account(
        self,
        bank_account: BankAccount,
        custom_name: str | None = None,
    ) -> tuple[Account, AccountMapping]:
        existing_mapping = await self._mapping_repo.find_by_iban(bank_account.iban)

        if existing_mapping is not None:
            existing_account = await self._account_repo.find_by_id(
                existing_mapping.accounting_account_id,
            )
            if existing_account is None:
                msg = (
                    f"Mapping exists for IBAN {bank_account.iban} but "
                    f"accounting account {existing_mapping.accounting_account_id} "
                    "not found"
                )
                raise ValueError(msg)

            if custom_name and existing_account.name != custom_name:
                existing_account.rename(custom_name)
                existing_mapping.update_account_name(custom_name)
                await self._account_repo.save(existing_account)
                await self._mapping_repo.save(existing_mapping)

            return existing_account, existing_mapping

        normalized_iban = normalize_iban(bank_account.iban) or ""
        existing_account_by_iban = await self._account_repo.find_by_iban(
            normalized_iban,
        )
        if existing_account_by_iban is not None:
            if existing_account_by_iban.account_type != AccountType.ASSET:
                msg = (
                    f"Found existing account for IBAN {normalized_iban} "
                    "but it is not an ASSET account: "
                    f"{existing_account_by_iban.account_type}"
                )
                raise ValueError(msg)

            if custom_name and existing_account_by_iban.name != custom_name:
                existing_account_by_iban.rename(custom_name)
                await self._account_repo.save(existing_account_by_iban)

            mapping = AccountMapping(
                iban=normalized_iban,
                accounting_account_id=existing_account_by_iban.id,
                account_name=custom_name or existing_account_by_iban.name,
                user_id=self._user_id,
                is_active=True,
            )
            await self._mapping_repo.save(mapping)
            return existing_account_by_iban, mapping

        account_name = custom_name or self._generate_account_name(bank_account)
        account_number = await self._generate_asset_account_number(normalized_iban)
        asset_account = Account(
            name=account_name,
            account_type=AccountType.ASSET,
            account_number=account_number,
            user_id=self._user_id,
            iban=normalized_iban,
            default_currency=Currency(bank_account.currency),
        )

        await self._account_repo.save(asset_account)
        mapping = AccountMapping(
            iban=normalized_iban,
            accounting_account_id=asset_account.id,
            account_name=account_name,
            user_id=self._user_id,
            is_active=True,
        )

        await self._mapping_repo.save(mapping)
        return asset_account, mapping

    async def _generate_asset_account_number(self, iban: str) -> str:
        normalized = normalize_iban(iban) or ""
        base = f"BA-{normalized[-8:]}"
        candidate = base
        suffix = 2
        while await self._account_repo.find_by_account_number(candidate):
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    async def import_multiple_bank_accounts(
        self,
        bank_accounts: list[BankAccount],
        custom_names: dict[str, str] | None = None,
    ) -> list[tuple[Account, AccountMapping]]:
        custom_names = custom_names or {}
        results = []
        for bank_account in bank_accounts:
            custom_name = custom_names.get(bank_account.iban)
            account, mapping = await self.import_bank_account(
                bank_account,
                custom_name=custom_name,
            )
            results.append((account, mapping))
        return results

    async def get_or_create_asset_account(self, iban: str) -> Account:
        normalized = normalize_iban(iban) or iban
        mapping = await self._mapping_repo.find_by_iban(normalized)
        if mapping is None:
            msg = f"No account mapping found for IBAN: {normalized}"
            raise ValueError(msg)

        account = await self._account_repo.find_by_id(mapping.accounting_account_id)
        if account is None:
            msg = (
                f"Mapping exists but account not found: {mapping.accounting_account_id}"
            )
            raise ValueError(msg)

        return account

    async def rename_bank_account(
        self,
        iban: str,
        new_name: str,
    ) -> BankAccountDTO:
        mapping = await self._mapping_repo.find_by_iban(iban)
        if mapping is None:
            msg = f"No account mapping found for IBAN: {iban}"
            raise ValueError(msg)

        account = await self._account_repo.find_by_id(mapping.accounting_account_id)
        if account is None:
            msg = (
                f"Mapping exists but account not found: {mapping.accounting_account_id}"
            )
            raise ValueError(msg)

        account.rename(new_name)
        mapping.update_account_name(new_name)

        await self._account_repo.save(account)
        await self._mapping_repo.save(mapping)

        return BankAccountDTO.from_entities(account, mapping)

    def _generate_account_name(self, bank_account: BankAccount) -> str:
        if bank_account.bank_name:
            return f"{bank_account.bank_name} - {bank_account.account_type}"
        return f"{bank_account.account_holder} - {bank_account.account_type}"
