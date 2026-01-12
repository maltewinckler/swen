"""FinTS Institute Directory - lookup bank endpoint information from CSV."""

import csv
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

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
        if self._loaded:
            return True

        try:
            self._parse_csv()
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

    def _parse_csv(self) -> None:
        if not self._csv_path.exists():
            msg = f"CSV file not found: {self._csv_path}"
            raise FileNotFoundError(msg) from FileNotFoundError

        with Path(self._csv_path).open(encoding=self._encoding, newline="") as f:
            reader = csv.reader(f, delimiter=";")

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

                except Exception as e:  # NOQA: PERF203
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


@lru_cache(maxsize=1)
def get_fints_institute_directory() -> FinTSInstituteDirectory:
    """Get the FinTS institute directory singleton."""
    return FinTSInstituteDirectory()
