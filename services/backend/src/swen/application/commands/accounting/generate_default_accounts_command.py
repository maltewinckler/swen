"""Generate a minimal chart of accounts for personal finance."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.repositories import AccountRepository
from swen.domain.accounting.value_objects import Currency

if TYPE_CHECKING:
    from swen.application.ports.identity import CurrentUser
    from swen.application.factories import RepositoryFactory


class ChartTemplate(str, Enum):
    """Available chart of accounts templates.

    MINIMAL: Simple categories for basic personal finance tracking.
        15 accounts covering essential income/expense categories.
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
                description="Employer payments, wages: Lohn, Gehalt, Arbeitgeber",
            ),
            Account(
                name="Sonstige Einnahmen",
                account_type=AccountType.INCOME,
                account_number="3100",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Refunds, rebates, interest, dividends, gifts",
            ),
            # Housing
            Account(
                name="Miete",
                account_type=AccountType.EXPENSE,
                account_number="4100",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Rent payments: Miete, Vermieter, Hausverwaltung",
            ),
            Account(
                name="Wohnen & Nebenkosten",
                account_type=AccountType.EXPENSE,
                account_number="4110",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Utilities: Strom, Gas, Wasser, Vattenfall, E.ON, GEZ, Rundfunk",  # NOQA: E501
            ),
            # Food & Dining
            Account(
                name="Lebensmittel",
                account_type=AccountType.EXPENSE,
                account_number="4200",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Supermarkets, groceries: REWE, Lidl, EDEKA, Aldi, Penny, Netto",  # NOQA: E501
            ),
            Account(
                name="Restaurants & Bars",
                account_type=AccountType.EXPENSE,
                account_number="4210",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Restaurants, cafes, bars, takeaway: Lieferando, Wolt, UberEats",  # NOQA: E501
            ),
            # Transportation
            Account(
                name="Transport & Mobilität",
                account_type=AccountType.EXPENSE,
                account_number="4300",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Public transport, fuel, car: BVG, DB, Deutsche Bahn, Uber, Bolt, Shell",  # NOQA: E501
            ),
            # Personal
            Account(
                name="Kleidung",
                account_type=AccountType.EXPENSE,
                account_number="4400",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Clothing, shoes: H&M, Zara, Zalando, About You, C&A",
            ),
            Account(
                name="Sport & Fitness",
                account_type=AccountType.EXPENSE,
                account_number="4500",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Gym, sports equipment: McFit, FitX, Urban Sports Club",
            ),
            Account(
                name="Gesundheit",
                account_type=AccountType.EXPENSE,
                account_number="4600",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Pharmacy, doctor, medical: Apotheke, Arzt, dm, Rossmann health",  # NOQA: E501
            ),
            # Entertainment & Lifestyle
            Account(
                name="Abonnements",
                account_type=AccountType.EXPENSE,
                account_number="4700",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Streaming, subscriptions: Netflix, Spotify, Amazon Prime, Disney+",  # NOQA: E501
            ),
            Account(
                name="Freizeit & Unterhaltung",
                account_type=AccountType.EXPENSE,
                account_number="4800",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Cinema, concerts, hobbies, games: Kino, Eventim, Steam",
            ),
            # Catch-all
            Account(
                name="Sonstiges",
                account_type=AccountType.EXPENSE,
                account_number="4900",
                user_id=self._user_id,
                default_currency=Currency("EUR"),
                description="Uncategorized expenses, miscellaneous purchases",
            ),
        ]
