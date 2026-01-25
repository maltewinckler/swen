"""Account balance query - read account balances without side effects."""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from swen.application.dtos.accounting import AccountBalanceDTO
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.repositories import (
    AccountRepository,
    TransactionRepository,
)
from swen.domain.accounting.services import AccountBalanceService
from swen.domain.shared.time import today_utc


class AccountBalanceQuery:
    """Query for retrieving account balance information.

    This is a read-only query that retrieves balances without
    modifying any state. It can be optimized independently
    (caching, read replicas, etc.).

    Hierarchy:
        - By default, balances are for the account only (not including children)
        - Set include_children=True to get rolled-up totals for parent accounts
        - The is_parent field indicates if the account has child accounts
    """

    def __init__(
        self,
        account_repo: AccountRepository,
        transaction_repo: TransactionRepository,
    ):
        self._account_repo = account_repo
        self._transaction_repo = transaction_repo
        self._balance_service = AccountBalanceService()

    async def get_balance_for_account(
        self,
        account_id: UUID,
        include_children: bool = False,
    ) -> Optional[AccountBalanceDTO]:
        account = await self._account_repo.find_by_id(account_id)
        if not account:
            return None

        transactions = await self._transaction_repo.find_by_account(account_id)

        if include_children:
            all_transactions = await self._transaction_repo.find_all()
            balance = await self._balance_service.calculate_balance_with_children(
                account,
                self._account_repo,
                all_transactions,
            )
        else:
            balance = self._balance_service.calculate_balance(account, transactions)

        is_parent = await self._account_repo.is_parent(account_id)

        return AccountBalanceDTO(
            account_id=str(account.id),
            account_name=account.name,
            account_number=account.account_number,
            account_type=account.account_type.name,
            balance=balance.amount,
            currency=str(balance.currency),
            balance_date=today_utc(),
            is_active=account.is_active,
            is_parent=is_parent,
            parent_id=str(account.parent_id) if account.parent_id else None,
            includes_children=include_children,
        )

    async def get_all_asset_balances(
        self,
        include_children: bool = False,
    ) -> List[AccountBalanceDTO]:
        return await self.get_balances_by_type(
            AccountType.ASSET,
            include_children=include_children,
        )

    async def get_total_assets(self) -> Decimal:
        balances = await self.get_all_asset_balances(include_children=False)
        return sum(
            (b.balance for b in balances if not b.is_parent),
            Decimal(0),
        )

    async def get_balances_by_type(
        self,
        account_type: AccountType,
        include_children: bool = False,
    ) -> List[AccountBalanceDTO]:
        accounts = await self._account_repo.find_by_type(account_type.value)

        all_transactions = None
        if include_children:
            all_transactions = await self._transaction_repo.find_all()

        balances = []
        for account in accounts:
            if not account.is_active:
                continue

            balance = await self._calculate_account_balance(
                account,
                include_children=include_children,
                all_transactions=all_transactions,
            )

            balances.append(balance)

        return balances

    async def _calculate_account_balance(
        self,
        account: Account,
        include_children: bool = False,
        all_transactions: Optional[list] = None,
    ) -> AccountBalanceDTO:
        if include_children and all_transactions is not None:
            balance = await self._balance_service.calculate_balance_with_children(
                account,
                self._account_repo,
                all_transactions,
            )
        else:
            transactions = await self._transaction_repo.find_by_account(account.id)
            balance = self._balance_service.calculate_balance(account, transactions)

        is_parent = await self._account_repo.is_parent(account.id)

        return AccountBalanceDTO(
            account_id=str(account.id),
            account_name=account.name,
            account_number=account.account_number,
            account_type=account.account_type.name,
            balance=balance.amount,
            currency=str(balance.currency),
            balance_date=today_utc(),
            is_active=account.is_active,
            is_parent=is_parent,
            parent_id=str(account.parent_id) if account.parent_id else None,
            includes_children=include_children,
        )
