#!/usr/bin/env python3
"""
Manual TAN Test - Run this to test TAN approval flow.

This script fetches a long transaction history (200+ days) which typically
requires TAN approval. When the TAN challenge appears, approve it manually.
"""

import asyncio
import logging
import os
import sys
import traceback
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "backend"))

from swen.domain.banking.value_objects.bank_credentials import BankCredentials
from swen.infrastructure.banking.geldstrom_adapter import GeldstromAdapter

# Load environment
root_dir = Path(__file__).parent.parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

# Enable debug logging
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO for less verbose output
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def tan_callback(challenge):
    """Handle TAN challenge - display to user."""
    print("\n" + "=" * 70)
    print("TAN CHALLENGE RECEIVED!")
    print("=" * 70)
    print(f"Method: {challenge.tan_method} - {challenge.tan_method_name}")
    print(f"Challenge: {challenge.challenge_text}")

    if challenge.hhduc_code:
        print(f"HHDUC Code: {challenge.hhduc_code}")

    if challenge.matrix_code:
        if isinstance(challenge.matrix_code, tuple):
            mime_type, data = challenge.matrix_code
            print(f"Photo TAN: {mime_type}, {len(data)} bytes")
            # Could save to file here if needed
        else:
            print(f"Matrix Code: {challenge.matrix_code}")

    if challenge.reference:
        print(f"Reference: {challenge.reference}")

    print("=" * 70)
    print("\nPlease approve the TAN using your TAN generator/app.")

    # Check if this is decoupled (app-based) TAN
    decoupled_methods = ["946", "900", "901"]  # SecureGo, pushTAN
    if challenge.tan_method in decoupled_methods:
        print("\n" + "�" * 35)
        print("📱 APP-BASED TAN (SecureGo)")
        print("🔴" * 35)
        print("\nWARNING:  ACTION REQUIRED:")
        print("   1. Check your SecureGo app on your phone")
        print("   2. Review and APPROVE the transaction")
        print("   3. Come back here and press ENTER")
        print("\n" + "🔴" * 35)
        input("\n👉 Press ENTER after you have confirmed in your app...")
        print("\nConfirmation received, polling bank...")
        return ""  # Empty string for decoupled TAN

    tan = input("Enter TAN: ")
    print("=" * 70)
    return tan


async def main():  # NOQA: PLR0915
    """Run the TAN test."""
    print("Manual TAN Test - Debug Mode")
    print("=" * 70)

    # Check if integration tests are enabled
    if os.getenv("RUN_INTEGRATION_TESTS", "").lower() not in ("1", "true", "yes"):
        print("Integration tests not enabled!")
        print("Set RUN_INTEGRATION_TESTS=1 in .env")
        return 1

    # Load credentials
    print("Loading credentials from .env...")
    try:
        blz = os.getenv("FINTS_BLZ")
        endpoint = os.getenv("FINTS_ENDPOINT")

        if not blz or not endpoint:
            print("Missing FINTS_BLZ or FINTS_ENDPOINT in .env")
            return 1

        credentials = BankCredentials.from_env(blz=blz, endpoint=endpoint)
        print(f"Credentials loaded for BLZ: {credentials.blz}")
    except Exception as e:
        print(f"Failed to load credentials: {e}")
        traceback.print_exc()
        return 1

    # Create Geldstrom adapter
    print("\nSetting up Geldstrom adapter...")
    adapter = GeldstromAdapter()

    # Set preferred TAN method and medium BEFORE connecting
    # Your bank supports: 946 (SecureGo app), 962 (manual), 972 (optical), 982 (photo)
    # Using 946 for SecureGo app (decoupled/push TAN)
    tan_method = os.getenv("FINTS_TAN_METHOD", "946")
    tan_medium = os.getenv("FINTS_TAN_MEDIUM", "SecureGo")
    print(f"Setting TAN method: {tan_method}")
    print(f"Setting TAN medium: {tan_medium}")
    print("  946 = SecureGo App (decoupled - will ask for app confirmation)")
    print("  962 = Smart-TAN plus manual")
    print("  972 = chipTAN optical")
    print("  982 = photoTAN")
    adapter.set_tan_method(tan_method)
    adapter.set_tan_medium(tan_medium)

    # NOTE: Setting TAN callback BEFORE connection
    print("Registering TAN callback...")
    await adapter.set_tan_callback(tan_callback)

    try:
        # Connect to bank
        print("\nConnecting to bank...")
        await adapter.connect(credentials)
        print("Connected successfully")

        # Fetch accounts
        print("\nFetching accounts...")
        accounts = await adapter.fetch_accounts()
        print(f"Found {len(accounts)} account(s)")

        if not accounts:
            print("No accounts available for testing")
            return 1

        # Display account info
        for i, acc in enumerate(accounts, 1):
            print(f"  {i}. {acc.iban} - {acc.account_holder}")

        # Use first account
        iban = accounts[0].iban
        print(f"\nTesting with account: {iban}")

        # Try different date ranges to find when TAN is required
        test_ranges = [
            ("30 days", 30),
            ("90 days", 90),
            ("180 days", 180),
            ("365 days", 365),
        ]

        for label, days in test_ranges:
            start_date = date.today() - timedelta(days=days)
            print(f"\n{'=' * 70}")
            print(f"Test: Fetching {label} of history ({start_date} to today)")
            print(f"{'=' * 70}")

            try:
                transactions = await adapter.fetch_transactions(
                    iban,
                    start_date=start_date,
                )
                print(f"Fetched {len(transactions)} transactions (no TAN required)")

                if transactions:
                    print(
                        f"   First: {transactions[0].booking_date} - {transactions[0].amount}",  # noqa: E501
                    )
                    print(
                        f"   Last: {transactions[-1].booking_date} - {transactions[-1].amount}",  # noqa: E501
                    )

            except Exception as e:
                print(f"Error fetching {label}: {e}")
                traceback.print_exc()
                print("\nContinuing with next test...")
                continue

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        traceback.print_exc()
        return 1

    finally:
        print("\n" + "=" * 70)
        print("Disconnecting...")
        await adapter.disconnect()
        print("Disconnected")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
