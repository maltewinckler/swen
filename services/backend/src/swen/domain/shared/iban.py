"""IBAN normalization utilities."""

from __future__ import annotations


def normalize_iban(value: str | None) -> str | None:
    """Normalize an IBAN for stable comparisons/storage.

    - Removes all spaces
    - Strips surrounding whitespace
    - Uppercases

    Returns None if value is None.
    """
    if value is None:
        return None
    normalized = value.strip().replace(" ", "").upper()
    return normalized or None


def extract_blz_from_iban(iban: str) -> str | None:
    """Extract German BLZ (bank code) from an IBAN.

    German IBANs have the format: DE + 2 check digits + 8-digit BLZ + 10-digit account.
    The BLZ is at positions 4-12 (0-indexed).

    Returns None if the IBAN is not a valid German IBAN.
    """
    if iban.startswith("DE") and len(iban) >= 12:
        return iban[4:12]
    return None
