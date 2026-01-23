"""Generate a minimal chart of accounts for personal finance."""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.repositories import AccountRepository
from swen.domain.accounting.value_objects import Currency

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.application.ports.identity import CurrentUser

logger = logging.getLogger(__name__)


class ChartTemplate(str, Enum):
    """Available chart of accounts templates.

    MINIMAL: Simple categories for basic personal finance tracking.
        13 accounts covering essential income/expense categories.
    """

    MINIMAL = "minimal"


class GenerateDefaultAccountsCommand:
    """Create a default chart of accounts for the current user."""

    def __init__(
        self,
        account_repository: AccountRepository,
        current_user: CurrentUser,
    ):
        self._account_repo = account_repository
        self._user_id = current_user.user_id

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> GenerateDefaultAccountsCommand:
        return cls(
            account_repository=factory.account_repository(),
            current_user=factory.current_user,
        )

    async def execute(
        self,
        template: ChartTemplate = ChartTemplate.MINIMAL,
    ) -> dict[str, int | bool | str]:
        accounts_created = {
            "ASSET": 0,
            "LIABILITY": 0,
            "EQUITY": 0,
            "INCOME": 0,
            "EXPENSE": 0,
        }

        existing_2000 = await self._account_repo.find_by_account_number("2000")
        if existing_2000:
            return {**accounts_created, "total": 0, "skipped": True}

        default_accounts = self._get_minimal_accounts()

        for account in default_accounts:
            await self._account_repo.save(account)
            accounts_created[account.account_type.value.upper()] += 1

        total = sum(accounts_created.values())
        return {
            **accounts_created,
            "total": total,
            "skipped": False,
            "template": template.value,
        }

    def _get_minimal_accounts(self) -> list[Account]:
        return [
            Account(
                name="Anfangssaldo",
                account_type=AccountType.EQUITY,
                account_number="2000",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
            ),
            Account(
                name="Gehalt & Lohn",
                account_type=AccountType.INCOME,
                account_number="3000",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Arbeitgeber, Lohn, Gehalt, Bezüge, Vergütung",
            ),
            Account(
                name="Sonstige Einnahmen",
                account_type=AccountType.INCOME,
                account_number="3100",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Erstattungen, Rückzahlungen, Zinsen, Dividenden",
            ),
            Account(
                name="Wohnen & Nebenkosten",
                account_type=AccountType.EXPENSE,
                account_number="4100",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Miete, Vermieter, Hausverwaltung, Strom, Gas, Wasser, Heizung, Vattenfall, E.ON, GEZ, Rundfunk",  # noqa: E501
            ),
            Account(
                name="Lebensmittel",
                account_type=AccountType.EXPENSE,
                account_number="4200",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Supermarkt, Einkauf, REWE, Lidl, EDEKA, Aldi, Penny, Netto, Kaufland",  # noqa: E501
            ),
            Account(
                name="Restaurants & Bars",
                account_type=AccountType.EXPENSE,
                account_number="4210",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Restaurant, Café, Bar, Imbiss, Lieferando, Wolt, UberEats",
            ),
            Account(
                name="Transport & Mobilität",
                account_type=AccountType.EXPENSE,
                account_number="4300",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="ÖPNV, Bahn, BVG, DB, Deutsche Bahn, Tanken, Benzin, Shell, Aral, Uber, Bolt, Taxi",  # noqa: E501
            ),
            Account(
                name="Kleidung",
                account_type=AccountType.EXPENSE,
                account_number="4400",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Bekleidung, Schuhe, H&M, Zara, Zalando, About You, C&A",
            ),
            Account(
                name="Sport & Fitness",
                account_type=AccountType.EXPENSE,
                account_number="4500",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Fitnessstudio, Sportverein, McFit, FitX",
            ),
            Account(
                name="Gesundheit",
                account_type=AccountType.EXPENSE,
                account_number="4600",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Apotheke, Arzt, Medikamente, Krankenhaus, dm, Rossmann",
            ),
            Account(
                name="Abonnements",
                account_type=AccountType.EXPENSE,
                account_number="4700",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Streaming, Abo, Netflix, Spotify, Amazon Prime, Disney+",
            ),
            Account(
                name="Freizeit & Unterhaltung",
                account_type=AccountType.EXPENSE,
                account_number="4800",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Kino, Konzert, Veranstaltung, Hobby, Spiele, Eventim",
            ),
            Account(
                name="Sonstiges",
                account_type=AccountType.EXPENSE,
                account_number="4900",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Sonstige Ausgaben, Verschiedenes",
            ),
        ]
