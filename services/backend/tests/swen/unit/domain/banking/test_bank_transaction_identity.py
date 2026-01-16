"""Tests for bank transaction identity hash computation."""

from datetime import date
from decimal import Decimal

from swen.domain.banking.value_objects import BankTransaction


def test_compute_identity_hash_is_deterministic():
    """Same transaction data should always produce the same identity hash."""
    transaction = BankTransaction(
        booking_date=date(2025, 10, 30),
        value_date=date(2025, 10, 30),
        amount=Decimal("100.50"),
        currency="EUR",
        purpose="Test payment",
        bank_reference="REF123456",
    )

    account_id = 42

    # Generate hash multiple times
    hash1 = transaction.compute_identity_hash(account_id)
    hash2 = transaction.compute_identity_hash(account_id)

    assert hash1 == hash2


def test_compute_identity_hash_changes_with_different_account():
    """Different account IDs should produce different hashes."""
    transaction = BankTransaction(
        booking_date=date(2025, 10, 30),
        value_date=date(2025, 10, 30),
        amount=Decimal("100.50"),
        currency="EUR",
        purpose="Test payment",
        bank_reference="REF123456",
    )

    hash1 = transaction.compute_identity_hash(account_identifier=1)
    hash2 = transaction.compute_identity_hash(account_identifier=2)

    assert hash1 != hash2


def test_compute_identity_hash_changes_with_different_amount():
    """Different amounts should produce different hashes."""
    base_data = {
        "booking_date": date(2025, 10, 30),
        "value_date": date(2025, 10, 30),
        "currency": "EUR",
        "purpose": "Test payment",
        "bank_reference": "REF123456",
    }

    tx1 = BankTransaction(**base_data, amount=Decimal("100.50"))
    tx2 = BankTransaction(**base_data, amount=Decimal("200.50"))

    account_id = 42

    hash1 = tx1.compute_identity_hash(account_id)
    hash2 = tx2.compute_identity_hash(account_id)
    assert hash1 != hash2


def test_compute_identity_hash_handles_missing_bank_reference():
    """Hash should work even without bank reference."""
    transaction = BankTransaction(
        booking_date=date(2025, 10, 30),
        value_date=date(2025, 10, 30),
        amount=Decimal("100.50"),
        currency="EUR",
        purpose="Test payment without reference",
        bank_reference=None,
    )

    account_id = 42

    # Should not raise an error
    identity_hash = transaction.compute_identity_hash(account_id)

    assert isinstance(identity_hash, str)
    assert len(identity_hash) > 0


def test_compute_identity_hash_returns_sha256_format():
    """Identity hash should be a valid SHA-256 hex digest (64 characters)."""
    transaction = BankTransaction(
        booking_date=date(2025, 10, 30),
        value_date=date(2025, 10, 30),
        amount=Decimal("100.50"),
        currency="EUR",
        purpose="Test payment",
    )

    identity_hash = transaction.compute_identity_hash(42)

    # SHA-256 produces 64 hex characters
    assert len(identity_hash) == 64
    # Should only contain hex characters
    assert all(c in "0123456789abcdef" for c in identity_hash)


def test_compute_transfer_hash_returns_sha256_format():
    """Transfer hash should be a valid SHA-256 hex digest (64 characters)."""
    transfer_hash = BankTransaction.compute_transfer_hash(
        iban_a="DE12345678901234567890",
        iban_b="DE98765432109876543210",
        booking_date=date(2025, 1, 5),
        amount=Decimal("500.00"),
    )

    # SHA-256 produces 64 hex characters
    assert len(transfer_hash) == 64
    # Should only contain hex characters
    assert all(c in "0123456789abcdef" for c in transfer_hash)


def test_compute_identity_hash_normalizes_applicant_iban():
    """Different formatting (spaces/case) of applicant IBAN should not change identity hash."""
    base = {
        "booking_date": date(2025, 10, 30),
        "value_date": date(2025, 10, 30),
        "amount": Decimal("100.50"),
        "currency": "EUR",
        "purpose": "Test payment",
        "bank_reference": None,
    }
    tx1 = BankTransaction(**base, applicant_iban="DE12 3456 7890 1234 5678 90")
    tx2 = BankTransaction(**base, applicant_iban="de12345678901234567890")
    assert tx1.compute_identity_hash(42) == tx2.compute_identity_hash(42)


def test_compute_transfer_hash_is_canonical_and_normalizes_ibans():
    """Transfer hash should be stable regardless of input order and spacing."""
    booking_date = date(2025, 1, 5)
    amount = Decimal("-700.00")
    a = "DE12 3456 7890 1234 5678 90"
    b = "de98 7654 3210 9876 5432 10"
    h1 = BankTransaction.compute_transfer_hash(a, b, booking_date, amount)
    h2 = BankTransaction.compute_transfer_hash(b, a, booking_date, amount)
    assert h1 == h2


def test_compute_identity_hash_with_same_data_without_reference():
    """Two transactions without bank reference but same data should have same hash."""
    base_data = {
        "booking_date": date(2025, 10, 30),
        "value_date": date(2025, 10, 30),
        "amount": Decimal("100.50"),
        "currency": "EUR",
        "purpose": "Exactly the same purpose text",
        "bank_reference": None,
    }

    tx1 = BankTransaction(**base_data)
    tx2 = BankTransaction(**base_data)

    account_id = 42

    hash1 = tx1.compute_identity_hash(account_id)
    hash2 = tx2.compute_identity_hash(account_id)
    assert hash1 == hash2
