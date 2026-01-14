"""Dashboard settings value object.

Controls which widgets are displayed on the dashboard and their configuration.
"""

from dataclasses import dataclass, field
from typing import Any

# Widget registry - defines all available widgets and their metadata
AVAILABLE_WIDGETS: dict[str, dict[str, Any]] = {
    "summary-cards": {
        "title": "Summary Cards",
        "description": "Key financial metrics at a glance",
        "category": "overview",
        "default_settings": {"days": 30},
    },
    "spending-pie": {
        "title": "Spending Breakdown",
        "description": "Pie chart showing spending by category",
        "category": "spending",
        "default_settings": {"months": 1},
    },
    "account-balances": {
        "title": "Account Balances",
        "description": "Bar chart of current account balances",
        "category": "overview",
        "default_settings": {},
    },
    "net-worth": {
        "title": "Net Worth Over Time",
        "description": "Track your net worth trend",
        "category": "overview",
        "default_settings": {"months": 12},
    },
    "income-over-time": {
        "title": "Income Over Time",
        "description": "Monthly income trend",
        "category": "income",
        "default_settings": {"months": 12},
    },
    "spending-over-time": {
        "title": "Spending Over Time",
        "description": "Monthly spending trend",
        "category": "spending",
        "default_settings": {"months": 12},
    },
    "net-income": {
        "title": "Net Income Over Time",
        "description": "Income minus expenses over time",
        "category": "overview",
        "default_settings": {"months": 12},
    },
    "savings-rate": {
        "title": "Savings Rate",
        "description": "Percentage of income saved each month",
        "category": "overview",
        "default_settings": {"months": 12},
    },
    "income-breakdown": {
        "title": "Income Sources",
        "description": "Pie chart showing income by source",
        "category": "income",
        "default_settings": {"months": 1},
    },
    "top-expenses": {
        "title": "Top Expenses",
        "description": "Highest spending categories",
        "category": "spending",
        "default_settings": {"months": 1, "limit": 5},
    },
    "month-comparison": {
        "title": "Month Comparison",
        "description": "Compare this month to previous",
        "category": "overview",
        "default_settings": {},
    },
    "single-account-spending": {
        "title": "Category Spending",
        "description": "Spending trend for a specific category",
        "category": "spending",
        "default_settings": {"months": 12, "account_id": None},
    },
    "sankey": {
        "title": "Cash Flow Sankey",
        "description": "Visual flow of income to expenses and savings",
        "category": "overview",
        "default_settings": {"days": 30},
    },
}

DEFAULT_ENABLED_WIDGETS: tuple[str, ...] = (
    "summary-cards",
    "spending-pie",
    "account-balances",
)


@dataclass(frozen=True)
class DashboardSettings:
    """Settings controlling dashboard widget display and configuration."""

    enabled_widgets: tuple[str, ...] = DEFAULT_ENABLED_WIDGETS
    widget_settings: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        # Validate all enabled widgets exist
        invalid_widgets = set(self.enabled_widgets) - set(AVAILABLE_WIDGETS.keys())
        if invalid_widgets:
            msg = f"Unknown widget IDs: {invalid_widgets}"
            raise ValueError(msg)

        # Validate widget_settings keys reference valid widgets
        invalid_settings = set(self.widget_settings.keys()) - set(
            AVAILABLE_WIDGETS.keys(),
        )
        if invalid_settings:
            msg = f"Widget settings reference unknown widgets: {invalid_settings}"
            raise ValueError(msg)

    @classmethod
    def default(cls) -> "DashboardSettings":
        return cls()

    def with_enabled_widgets(
        self,
        widgets: list[str] | tuple[str, ...],
    ) -> "DashboardSettings":
        return DashboardSettings(
            enabled_widgets=tuple(widgets),
            widget_settings=self.widget_settings,
        )

    def with_widget_settings(
        self,
        widget_id: str,
        settings: dict[str, Any],
    ) -> "DashboardSettings":
        if widget_id not in AVAILABLE_WIDGETS:
            msg = f"Unknown widget ID: {widget_id}"
            raise ValueError(msg)

        new_settings = dict(self.widget_settings)
        new_settings[widget_id] = settings
        return DashboardSettings(
            enabled_widgets=self.enabled_widgets,
            widget_settings=new_settings,
        )

    def with_all_widget_settings(
        self,
        settings: dict[str, dict[str, Any]],
    ) -> "DashboardSettings":
        return DashboardSettings(
            enabled_widgets=self.enabled_widgets,
            widget_settings=settings,
        )

    def get_widget_settings(self, widget_id: str) -> dict[str, Any]:
        if widget_id not in AVAILABLE_WIDGETS:
            msg = f"Unknown widget ID: {widget_id}"
            raise ValueError(msg)

        defaults = AVAILABLE_WIDGETS[widget_id].get("default_settings", {})
        user_settings = self.widget_settings.get(widget_id, {})
        return {**defaults, **user_settings}

    def is_widget_enabled(self, widget_id: str) -> bool:
        return widget_id in self.enabled_widgets

    def enable_widget(self, widget_id: str) -> "DashboardSettings":
        if widget_id not in AVAILABLE_WIDGETS:
            msg = f"Unknown widget ID: {widget_id}"
            raise ValueError(msg)

        if widget_id in self.enabled_widgets:
            return self

        return self.with_enabled_widgets((*self.enabled_widgets, widget_id))

    def disable_widget(self, widget_id: str) -> "DashboardSettings":
        if widget_id not in self.enabled_widgets:
            return self

        new_widgets = tuple(w for w in self.enabled_widgets if w != widget_id)
        return self.with_enabled_widgets(new_widgets)

    def reorder_widgets(self, new_order: list[str]) -> "DashboardSettings":
        # Validate all widgets in new_order are currently enabled
        new_set = set(new_order)
        current_set = set(self.enabled_widgets)

        if new_set != current_set:
            missing = current_set - new_set
            extra = new_set - current_set
            if missing:
                msg = f"Reorder missing widgets: {missing}"
                raise ValueError(msg)
            if extra:
                msg = f"Reorder includes disabled widgets: {extra}"
                raise ValueError(msg)

        return self.with_enabled_widgets(new_order)

    @classmethod
    def get_available_widgets(cls) -> dict[str, dict[str, Any]]:
        return AVAILABLE_WIDGETS.copy()
