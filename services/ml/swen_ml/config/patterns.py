"""Known merchant patterns and keywords for Tier 1 classification."""

import re

# Precompiled pattern for merchant extraction
MERCHANT_PATTERN = re.compile(r"^([A-ZÄÖÜ][A-ZÄÖÜa-zäöüß]*)", re.IGNORECASE)

# Known merchants → account number
# These are common German merchants that can be reliably classified
KNOWN_MERCHANTS: dict[str, str] = {
    # Supermarkets → 4200 Lebensmittel
    "REWE": "4200",
    "EDEKA": "4200",
    "LIDL": "4200",
    "ALDI": "4200",
    "PENNY": "4200",
    "NETTO": "4200",
    "KAUFLAND": "4200",
    # Bakeries → 4200 Lebensmittel
    "BAECKEREI": "4200",
    "BACKWERK": "4200",
    "KAMPS": "4200",
    # Drugstores → 4600 Gesundheit
    "DM": "4600",
    "ROSSMANN": "4600",
    "MUELLER": "4600",
    # Restaurants & Cafes → 4210 Restaurants & Bars
    "STARBUCKS": "4210",
    "MCDONALDS": "4210",
    "BURGERKING": "4210",
    "LIEFERANDO": "4210",
    "TAKEAWAY": "4210",
    # Streaming → 4700 Abonnements
    "SPOTIFY": "4700",
    "NETFLIX": "4700",
    "DISNEY": "4700",
    "AMAZON": "4700",
    "DAZN": "4700",
    # Telecom → 4700 Abonnements
    "TELEKOM": "4700",
    "VODAFONE": "4700",
    "O2": "4700",
    "CONGSTAR": "4700",
    # Transport → 4300 Transport & Mobilität
    "ARAL": "4300",
    "SHELL": "4300",
    "TOTAL": "4300",
    "HVV": "4300",
    "BVG": "4300",
    "MVV": "4300",
    "UBER": "4300",
    "TIER": "4300",
    "NEXTBIKE": "4300",
    # Fitness → 4500 Sport & Fitness
    "FITX": "4500",
    "MCFIT": "4500",
    "URBANSPORTS": "4500",
    # Insurance (no specific category, goes to Sonstiges)
    "HUK": "4900",
    "ALLIANZ": "4900",
    "ERGO": "4900",
    "AXA": "4900",
}

# Keywords in purpose text → account number
KEYWORDS: dict[str, str] = {
    # Housing → 4100 Wohnen & Nebenkosten
    "miete": "4100",
    "nebenkosten": "4100",
    "strom": "4100",
    "gas": "4100",
    "heizung": "4100",
    "rundfunk": "4100",
    "gez": "4100",
    # Income → 3000 Gehalt & Lohn
    "gehalt": "3000",
    "lohn": "3000",
    "bezuege": "3000",
    # Other income → 3100 Sonstige Einnahmen
    "erstattung": "3100",
    "rueckzahlung": "3100",
    "zinsen": "3100",
}


def normalize_merchant(name: str) -> str | None:
    """Extract and normalize merchant name from counterparty."""
    if not name:
        return None
    match = MERCHANT_PATTERN.match(name.strip())
    if match:
        return match.group(1).upper()
    return None
