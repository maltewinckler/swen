"""Batch counter-account resolution service.

Pure batch processor: takes a list of bank transactions, calls the proposal
port once, validates proposals against accounting business rules, detects
internal transfers, and returns a dict of resolved counter-accounts ready
for import.

No streaming, no chunking — the caller is responsible for batching.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from swen.domain.accounting.services.classification_rules import ClassificationRules
from swen.domain.accounting.well_known_accounts import WellKnownAccounts
from swen.domain.banking.repositories import StoredBankTransaction
from swen.domain.integration.value_objects import (
    CounterAccountProposal,
    ResolvedCounterAccount,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.accounting.entities import Account
    from swen.domain.accounting.repositories import AccountRepository
    from swen.domain.integration.ports.counter_account_proposal_port import (
        CounterAccountProposalPort,
    )
    from swen.domain.integration.repositories import AccountMappingRepository
    from swen.domain.shared.current_user import CurrentUser

logger = logging.getLogger(__name__)


class CounterAccountBatchService:
    """Resolve counter-accounts for a batch of bank transactions.

    Calls the proposal port once for the entire batch, validates each
    proposal against accounting direction rules, and falls back to
    well-known default accounts when a proposal is invalid or missing.
    """

    def __init__(
        self,
        proposal_port: CounterAccountProposalPort,
        account_repository: AccountRepository,
        mapping_repository: AccountMappingRepository,
        current_user: CurrentUser,
    ) -> None:
        self._port = proposal_port
        self._account_repo = account_repository
        self._mapping_repo = mapping_repository
        self._user_id = current_user.user_id

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        proposal_port: CounterAccountProposalPort,
    ) -> CounterAccountBatchService:
        return cls(
            proposal_port=proposal_port,
            account_repository=factory.account_repository(),
            mapping_repository=factory.account_mapping_repository(),
            current_user=factory.current_user,
        )

    async def resolve_batch(
        self,
        stored_transactions: list[StoredBankTransaction],
    ) -> dict[UUID, ResolvedCounterAccount]:
        """Resolve counter-accounts for a batch of bank transactions.

        Resolution order per transaction:
        1. Check if counterparty maps to an internal account → ``source="internal"``
        2. Otherwise call proposal port → validate → ``source="ai" | "fallback"``

        Parameters
        ----------
        stored_transactions
            The batch of stored bank transactions to resolve.

        Returns
        -------
        dict[UUID, ResolvedCounterAccount]
            Mapping from ``StoredBankTransaction.id`` to the resolved
            counter-account, guaranteed to contain an entry for every
            input transaction.
        """
        # Step 1: Detect internal transfers
        results: dict[UUID, ResolvedCounterAccount] = {}
        remaining: list[StoredBankTransaction] = []

        for stored in stored_transactions:
            internal = await self._detect_internal(stored)
            if internal is not None:
                results[stored.id] = internal
            else:
                remaining.append(stored)

        if not remaining:
            return results

        # Step 2: ML classification for non-internal transactions
        proposals = await self._port.classify_batch(
            user_id=self._user_id,
            transactions=remaining,
        )

        if proposals is None:
            logger.warning("Proposal port unavailable — using fallback for all")
            fallbacks = await self._build_all_fallback(remaining)
            results.update(fallbacks)
            return results

        ml_results = await self._validate_proposals(proposals, remaining)
        results.update(ml_results)

        # Post-condition: every input transaction must have a resolution
        missing = [s.id for s in stored_transactions if s.id not in results]
        if missing:
            msg = f"Failed to resolve acc for {len(missing)} transaction(s): {missing}"
            raise RuntimeError(msg)

        return results

    async def _detect_internal(
        self,
        stored: StoredBankTransaction,
    ) -> ResolvedCounterAccount | None:
        """Check if the counterparty IBAN maps to an internal account.

        Returns a ``ResolvedCounterAccount(source="internal")`` if the
        counterparty is an own account, otherwise ``None``.
        """
        counterparty_iban = stored.transaction.applicant_iban
        if not counterparty_iban:
            return None

        mapping = await self._mapping_repo.find_by_iban(counterparty_iban)
        if not mapping:
            return None

        account = await self._account_repo.find_by_id(mapping.accounting_account_id)
        if account is None:
            logger.warning(
                "Mapping for IBAN %s references non-existent account %s",
                counterparty_iban,
                mapping.accounting_account_id,
            )
            return None

        return ResolvedCounterAccount(
            account=account,
            confidence=None,
        )

    async def _validate_proposals(
        self,
        proposals: list[CounterAccountProposal],
        stored_transactions: list[StoredBankTransaction],
    ) -> dict[UUID, ResolvedCounterAccount]:
        """Validate proposals and resolve to domain accounts.

        For each proposal: look up the account, validate direction, fall
        back if invalid or missing.
        """
        txn_by_id = {s.id: s for s in stored_transactions}
        results: dict[UUID, ResolvedCounterAccount] = {}

        for proposal in proposals:
            stored = txn_by_id.get(proposal.transaction_id)
            if stored is None:
                logger.warning(
                    "Proposal for unknown transaction_id=%s",
                    proposal.transaction_id,
                )
                continue

            resolved = await self._resolve_single_proposal(proposal, stored)
            results[proposal.transaction_id] = resolved

        # Fill in any transactions that didn't get a proposal
        for stored in stored_transactions:
            if stored.id not in results:
                fallback = await self._get_fallback_account(
                    stored.transaction.is_debit(),
                )
                results[stored.id] = ResolvedCounterAccount(
                    account=fallback,
                    confidence=None,
                )

        return results

    async def _resolve_single_proposal(
        self,
        proposal: CounterAccountProposal,
        stored: StoredBankTransaction,
    ) -> ResolvedCounterAccount:
        """Resolve a single proposal to a validated account or fallback."""
        if not proposal.counter_account_id:
            fallback = await self._get_fallback_account(
                stored.transaction.is_debit(),
            )
            return ResolvedCounterAccount(
                account=fallback,
                confidence=proposal.confidence,
            )

        account = await self._account_repo.find_by_id(proposal.counter_account_id)
        if account is None:
            logger.warning(
                "Proposal account_id=%s not found — falling back",
                proposal.counter_account_id,
            )
            fallback = await self._get_fallback_account(
                stored.transaction.is_debit(),
            )
            return ResolvedCounterAccount(
                account=fallback,
                confidence=proposal.confidence,
            )

        is_money_outflow = stored.transaction.is_debit()
        if not ClassificationRules.is_valid_counter_direction(
            is_money_outflow=is_money_outflow,
            account_type=account.account_type,
        ):
            logger.warning(
                "Direction mismatch: is_money_outflow=%s but proposal "
                "returned %s account %s (%s) — falling back",
                is_money_outflow,
                account.account_type.value,
                account.account_number,
                account.name,
            )
            fallback = await self._get_fallback_account(is_money_outflow)
            return ResolvedCounterAccount(
                account=fallback,
                confidence=proposal.confidence,
            )

        return ResolvedCounterAccount(
            account=account,
            confidence=proposal.confidence,
        )

    async def _get_fallback_account(self, is_expense: bool) -> Account:
        """Look up the well-known fallback account."""
        account_number = (
            WellKnownAccounts.FALLBACK_EXPENSE
            if is_expense
            else WellKnownAccounts.FALLBACK_INCOME
        )
        account = await self._account_repo.find_by_account_number(account_number)
        if not account:
            msg = f"Fallback account ({account_number}) not found"
            raise ValueError(msg)
        return account

    async def _build_all_fallback(
        self,
        stored_transactions: list[StoredBankTransaction],
    ) -> dict[UUID, ResolvedCounterAccount]:
        """Build fallback results for all transactions (port unavailable)."""
        results: dict[UUID, ResolvedCounterAccount] = {}
        for stored in stored_transactions:
            fallback = await self._get_fallback_account(
                stored.transaction.is_debit(),
            )
            results[stored.id] = ResolvedCounterAccount(
                account=fallback,
                confidence=None,
            )
        return results
