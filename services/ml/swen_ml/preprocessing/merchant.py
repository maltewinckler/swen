"""Merchant name extraction and normalization."""

import re

# Pattern to extract merchant name from counterparty
# Matches: "REWE.Filiale/Berlin" -> "REWE"
#          "EDEKA.Hundrieser/Essen" -> "EDEKA"
MERCHANT_PATTERN = re.compile(
    r"^([A-ZÄÖÜ][A-ZÄÖÜa-zäöüß]*)",
    re.IGNORECASE,
)

# Common prefixes to strip
STRIP_PREFIXES = {"PAYPAL", "SUMUP", "ZETTLE"}


def extract_merchant(counterparty: str | None) -> str | None:
    """Extract normalized merchant name from counterparty string.

    Examples:
        "REWE.Filiale.Nord/Hamburg" -> "REWE"
        "PAYPAL..SPOTIFY/35314369001" -> "SPOTIFY"
        "Stadtwerke Hamburg" -> "STADTWERKE"
    """
    if not counterparty:
        return None

    text = counterparty.strip().upper()

    # Handle PayPal-style: "PAYPAL..MERCHANT/..."
    if text.startswith("PAYPAL"):
        parts = re.split(r"[./]+", text)
        for part in parts[1:]:  # Skip PAYPAL
            if part and part not in STRIP_PREFIXES and len(part) > 2:
                return part
        return None

    # Standard extraction
    match = MERCHANT_PATTERN.match(text)
    if match:
        merchant = match.group(1).upper()
        if merchant not in STRIP_PREFIXES:
            return merchant

    return None


def normalize_counterparty(counterparty: str | None) -> str:
    """Normalize counterparty for comparison."""
    if not counterparty:
        return ""
    # Remove special characters, lowercase
    return re.sub(r"[^a-zA-ZäöüÄÖÜß0-9]", "", counterparty.lower())
