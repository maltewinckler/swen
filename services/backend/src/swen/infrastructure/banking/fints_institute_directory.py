"""FinTS Institute Directory - lookup bank endpoint information from CSV."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from swen.infrastructure.banking.fints_config_repository import (
        FinTSConfigRepository,
    )

from swen_config import get_config_dir

logger = logging.getLogger(__name__)

# CSV column indices (0-based)
COL_BLZ = 1
COL_BIC = 2
COL_NAME = 3
COL_CITY = 4
COL_PIN_TAN_URL = 24  # "PIN/TAN-Zugang URL"


@dataclass(frozen=True)
class FinTSInstituteInfo:
    """Information about a FinTS-enabled bank institute."""

    blz: str
    bic: str
    name: str
    city: str
    endpoint_url: str

    def __str__(self) -> str:
        """String representation."""
        return f"{self.name} ({self.blz})"


class FinTSInstituteDirectoryError(Exception):
    """Base exception for FinTS Institute Directory errors."""


class CsvFileNotFoundError(FinTSInstituteDirectoryError):
    """Raised when the CSV file cannot be found."""


class CsvParseError(FinTSInstituteDirectoryError):
    """Raised when the CSV file cannot be parsed."""


class FinTSInstituteDirectory:
    """
    Directory service for looking up FinTS bank institute information.

    Parses the CSV file from Deutsche Kreditwirtschaft containing
    FinTS endpoint information for German banks.

    The CSV is expected to be semicolon-delimited with CP1252 encoding.
    """

    def __init__(
        self,
        csv_path: Optional[Path] = None,
        *,
        encoding: str = "cp1252",  # standard by FinTS specification
    ):
        self._csv_path = csv_path or (get_config_dir() / "fints_institute.csv")
        self._encoding = encoding
        self._blz_index: dict[str, FinTSInstituteInfo] = {}
        self._bic_index: dict[str, FinTSInstituteInfo] = {}
        self._loaded = False
        self._load_error: Optional[Exception] = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> Optional[Exception]:
        return self._load_error

    @property
    def institute_count(self) -> int:
        return len(self._blz_index)

    def load(self) -> bool:
        """Load institute data from CSV file on disk."""
        if self._loaded:
            return True

        try:
            self._parse_csv_file()
            self._loaded = True
            self._load_error = None
            logger.info(
                "Loaded %d FinTS institutes from %s",
                len(self._blz_index),
                self._csv_path,
            )
            return True

        except FileNotFoundError:
            self._load_error = CsvFileNotFoundError(
                f"CSV file not found: {self._csv_path}",
            )
            logger.warning("FinTS institute CSV not found: %s", self._csv_path)
            return False

        except Exception as e:
            self._load_error = CsvParseError(f"Failed to parse CSV: {e}")
            logger.warning("Failed to parse FinTS institute CSV: %s", e)
            return False

    def load_from_bytes(self, csv_content: bytes, encoding: str = "cp1252") -> bool:
        """Load institute data from raw CSV bytes.

        Used for loading CSV data stored in the database.

        Parameters
        ----------
        csv_content
            Raw CSV file bytes.
        encoding
            Character encoding of the CSV content.

        Returns
        -------
        True if loading succeeded, False otherwise.
        """
        if self._loaded:
            return True

        try:
            text = csv_content.decode(encoding)
            reader = csv.reader(StringIO(text), delimiter=";")
            self._process_csv_reader(reader)
            self._loaded = True
            self._load_error = None
            logger.info(
                "Loaded %d FinTS institutes from bytes (%d bytes)",
                len(self._blz_index),
                len(csv_content),
            )
            return True

        except (UnicodeDecodeError, ValueError) as e:
            self._load_error = CsvParseError(f"Failed to decode CSV bytes: {e}")
            logger.warning("Failed to decode FinTS institute CSV bytes: %s", e)
            return False

        except Exception as e:
            self._load_error = CsvParseError(f"Failed to parse CSV bytes: {e}")
            logger.warning("Failed to parse FinTS institute CSV bytes: %s", e)
            return False

    def invalidate_cache(self) -> None:
        """Clear loaded data and force reload on next access.

        Called when a new CSV is uploaded via the admin API.
        """
        self._loaded = False
        self._load_error = None
        self._blz_index.clear()
        self._bic_index.clear()

    def _parse_csv_file(self) -> None:
        """Parse CSV from file on disk."""
        if not self._csv_path.exists():
            msg = f"CSV file not found: {self._csv_path}"
            raise FileNotFoundError(msg) from FileNotFoundError

        with Path(self._csv_path).open(encoding=self._encoding, newline="") as f:
            reader = csv.reader(f, delimiter=";")
            self._process_csv_reader(reader)

    def _process_csv_reader(self, reader: csv.reader) -> None:  # type: ignore[type-arg]
        """Process a CSV reader and populate indexes."""
        # Skip header row
        try:
            next(reader)
        except StopIteration:
            msg = "CSV file is empty"
            raise CsvParseError(msg) from StopIteration

        row_count = 0
        for row_num, row in enumerate(reader, start=2):
            try:
                institute = self._parse_row(row)
                if institute:
                    # Only store first occurrence of each BLZ
                    # (same bank may have multiple locations)
                    if institute.blz not in self._blz_index:
                        self._blz_index[institute.blz] = institute

                    # BIC index (may have multiple BLZs per BIC)
                    if institute.bic and institute.bic not in self._bic_index:
                        self._bic_index[institute.bic] = institute

                    row_count += 1

            except Exception as e:
                # Log but continue parsing other rows
                logger.debug("Skipping row %d: %s", row_num, e)
                continue

        if row_count == 0:
            msg = "No valid institute entries found in CSV"
            raise CsvParseError(msg) from ValueError

    def _parse_row(self, row: list[str]) -> Optional[FinTSInstituteInfo]:
        # Ensure row has enough columns
        if len(row) <= COL_PIN_TAN_URL:
            return None

        blz = row[COL_BLZ].strip()
        bic = row[COL_BIC].strip()
        name = row[COL_NAME].strip()
        city = row[COL_CITY].strip()
        endpoint_url = row[COL_PIN_TAN_URL].strip()

        # Skip if no BLZ or no endpoint URL
        if not blz or not endpoint_url:
            return None

        # Validate BLZ format (8 digits)
        if not blz.isdigit() or len(blz) != 8:
            return None

        # Validate endpoint URL starts with https
        if not endpoint_url.startswith("http"):
            return None

        return FinTSInstituteInfo(
            blz=blz,
            bic=bic,
            name=name,
            city=city,
            endpoint_url=endpoint_url,
        )

    def find_by_blz(self, blz: str) -> Optional[FinTSInstituteInfo]:
        # Lazy load on first access
        if not self._loaded:
            self.load()

        # Normalize BLZ (remove spaces, ensure 8 digits)
        blz = blz.strip().replace(" ", "")

        return self._blz_index.get(blz)

    def find_by_bic(self, bic: str) -> Optional[FinTSInstituteInfo]:
        # Lazy load on first access
        if not self._loaded:
            self.load()

        # Normalize BIC (uppercase, no spaces)
        bic = bic.strip().upper().replace(" ", "")

        return self._bic_index.get(bic)


# ═══════════════════════════════════════════════════════════════
#           Module-Level Accessors and Caching
# ═══════════════════════════════════════════════════════════════

# File-based singleton (for testing / legacy use)
_file_based_directory: FinTSInstituteDirectory | None = None


def get_fints_institute_directory() -> FinTSInstituteDirectory:
    """Get the file-based FinTS institute directory singleton.

    Kept for backward compatibility and testing.
    Production code should use ``get_fints_institute_directory_async``.
    """
    global _file_based_directory  # noqa: PLW0603
    if _file_based_directory is None:
        _file_based_directory = FinTSInstituteDirectory()
    return _file_based_directory


# DB-backed singleton (production use)
_db_backed_directory: FinTSInstituteDirectory | None = None


async def get_fints_institute_directory_async(
    config_repo: FinTSConfigRepository,
) -> FinTSInstituteDirectory:
    """Get DB-backed FinTS institute directory with in-memory caching.

    Loads the institute CSV from the database on first call and caches
    the parsed result. Subsequent calls return the cached directory
    until ``invalidate_fints_directory_cache`` is called.

    Parameters
    ----------
    config_repo
        Repository providing access to the stored CSV data.

    Returns
    -------
    Loaded FinTSInstituteDirectory instance.

    Raises
    ------
    FinTSInstituteDirectoryError
        If configuration is missing or CSV cannot be parsed.
    """
    global _db_backed_directory  # noqa: PLW0603
    if _db_backed_directory is not None and _db_backed_directory.is_loaded:
        return _db_backed_directory

    config = await config_repo.get_configuration()
    if config is None:
        msg = (
            "FinTS institute directory not configured. "
            "An administrator must upload the institute CSV file."
        )
        raise FinTSInstituteDirectoryError(msg)

    directory = FinTSInstituteDirectory()
    if not directory.load_from_bytes(config.csv_content, config.csv_encoding):
        raise directory.load_error or FinTSInstituteDirectoryError(
            "Failed to load institute directory from database",
        )

    _db_backed_directory = directory
    return _db_backed_directory


def invalidate_fints_directory_cache() -> None:
    """Invalidate the cached DB-backed directory.

    Must be called after the admin uploads a new CSV so that
    subsequent lookups use the updated data.
    """
    global _db_backed_directory  # noqa: PLW0603
    _db_backed_directory = None
