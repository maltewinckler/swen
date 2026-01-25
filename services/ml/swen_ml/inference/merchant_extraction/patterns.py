"""Known merchant patterns and constants."""

import re

# Pattern to extract merchant name from counterparty
MERCHANT_PATTERN = re.compile(
    r"^([A-ZÄÖÜ][A-ZÄÖÜa-zäöüß]*)",
    re.IGNORECASE,
)

# Payment providers to strip
STRIP_PREFIXES = {"PAYPAL", "SUMUP", "ZETTLE", "STRIPE", "KLARNA"}

# Known merchants (for reference/validation)
# These could be used for pattern matching or validation
KNOWN_MERCHANTS: set[str] = {
    # Supermarkets
    "REWE",
    "EDEKA",
    "LIDL",
    "ALDI",
    "PENNY",
    "NETTO",
    "KAUFLAND",
    # Bakeries
    "BAECKEREI",
    "BACKWERK",
    "KAMPS",
    # Drugstores
    "DM",
    "ROSSMANN",
    "MUELLER",
    # Restaurants & Cafes
    "STARBUCKS",
    "MCDONALDS",
    "BURGERKING",
    "LIEFERANDO",
    "TAKEAWAY",
    # Streaming
    "SPOTIFY",
    "NETFLIX",
    "DISNEY",
    "AMAZON",
    "DAZN",
    # Telecom
    "TELEKOM",
    "VODAFONE",
    "O2",
    "CONGSTAR",
    # Transport
    "ARAL",
    "SHELL",
    "TOTAL",
    "HVV",
    "BVG",
    "MVV",
    "UBER",
    "TIER",
    "NEXTBIKE",
    # Fitness
    "FITX",
    "MCFIT",
    "URBANSPORTS",
    # Insurance
    "HUK",
    "ALLIANZ",
    "ERGO",
    "AXA",
}
