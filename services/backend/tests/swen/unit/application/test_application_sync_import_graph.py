"""Import-graph guard for the application sync write path.

Parses each module in the application sync write path with ``ast`` and asserts
that no ``sqlalchemy.*`` or ``swen.infrastructure.*`` import appears outside an
``if TYPE_CHECKING:`` block.  This test falsifies the AGENTS.md §2 violation
("Application depends only on domain and its own ports") if it ever returns.

Validates: Requirements 4.1, 4.2, 15.2
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BACKEND_SRC = Path(__file__).resolve().parents[6] / "services" / "backend" / "src"

_FORBIDDEN_PREFIXES = ("sqlalchemy", "swen.infrastructure")


def _is_type_checking_block(node: ast.If) -> bool:
    """Return True when *node* is an ``if TYPE_CHECKING:`` guard."""
    test = node.test
    # Plain ``if TYPE_CHECKING:``
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    # ``if typing.TYPE_CHECKING:``
    if (
        isinstance(test, ast.Attribute)
        and test.attr == "TYPE_CHECKING"
        and isinstance(test.value, ast.Name)
        and test.value.id == "typing"
    ):
        return True
    return False


def _collect_type_checking_lines(tree: ast.Module) -> set[int]:
    """Return line numbers of all nodes inside ``if TYPE_CHECKING:`` blocks."""
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _is_type_checking_block(node):
            for child in ast.walk(node):
                if hasattr(child, "lineno"):
                    lines.add(child.lineno)  # type: ignore[attr-defined]
    return lines


def _collect_forbidden_imports_outside_type_checking(source: str) -> list[str]:
    """Return forbidden import names found outside TYPE_CHECKING guards."""
    tree = ast.parse(source)
    type_checking_lines = _collect_type_checking_lines(tree)
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if node.lineno in type_checking_lines:  # type: ignore[attr-defined]
            continue

        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if any(
                    name == p or name.startswith(p + ".") for p in _FORBIDDEN_PREFIXES
                ):
                    violations.append(name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if any(
                module == p or module.startswith(p + ".") for p in _FORBIDDEN_PREFIXES
            ):
                violations.append(module)

    return violations


def _check_module_file(rel_path: str) -> list[str]:
    """Parse the file at *rel_path* (relative to backend src) and return violations."""
    full_path = _BACKEND_SRC / rel_path
    source = full_path.read_text(encoding="utf-8")
    return _collect_forbidden_imports_outside_type_checking(source)


# ---------------------------------------------------------------------------
# Parametrised test
# ---------------------------------------------------------------------------

_MODULES_UNDER_TEST = [
    # application/services/integration/
    "swen/application/services/integration/transaction_import_service.py",
    # application/services/integration/bank_account_sync/
    "swen/application/services/integration/bank_account_sync/bank_account_sync_service.py",
    # application/commands/integration/
    "swen/application/commands/integration/sync_bank_accounts_command.py",
]


@pytest.mark.parametrize("rel_path", _MODULES_UNDER_TEST)
def test_no_forbidden_runtime_imports(rel_path: str) -> None:
    """Assert no sqlalchemy.* or swen.infrastructure.* imports outside TYPE_CHECKING.

    Any such import that is NOT guarded by ``if TYPE_CHECKING:`` would be
    reachable at runtime and would violate the application-layer isolation
    rule in AGENTS.md §2.

    Validates: Requirements 4.1, 4.2, 15.2
    """
    violations = _check_module_file(rel_path)
    assert not violations, (
        f"{rel_path} has forbidden runtime imports: {violations!r}\n"
        "Move them inside an `if TYPE_CHECKING:` block or replace with a "
        "Protocol port in `application/ports/`."
    )
