"""Unit tests for FinTSInstituteDirectory."""

from pathlib import Path

import pytest

from swen.infrastructure.banking.fints_institute_directory import (
    CsvFileNotFoundError,
    CsvParseError,
    FinTSInstituteDirectory,
    FinTSInstituteInfo,
)
from swen_config import get_config_dir

# Path to real CSV file (if available)
_REAL_CSV_PATH = get_config_dir() / "fints_institute.csv"


class TestFinTSInstituteInfo:
    """Tests for the FinTSInstituteInfo dataclass."""

    def test_create_institute_info(self):
        """Should create an immutable institute info object."""
        info = FinTSInstituteInfo(
            blz="50031000",
            bic="TRODDEF1XXX",
            name="Triodos Bank Deutschland",
            city="Frankfurt am Main",
            endpoint_url="https://fints2.atruvia.de/cgi-bin/hbciservlet",
        )

        assert info.blz == "50031000"
        assert info.bic == "TRODDEF1XXX"
        assert info.name == "Triodos Bank Deutschland"
        assert info.city == "Frankfurt am Main"
        assert info.endpoint_url == "https://fints2.atruvia.de/cgi-bin/hbciservlet"

    def test_institute_info_is_immutable(self):
        """Should not allow modification after creation."""
        info = FinTSInstituteInfo(
            blz="50031000",
            bic="TRODDEF1XXX",
            name="Test Bank",
            city="Test City",
            endpoint_url="https://example.com",
        )

        with pytest.raises(AttributeError):
            info.blz = "12345678"  # type: ignore

    def test_str_representation(self):
        """Should have a readable string representation."""
        info = FinTSInstituteInfo(
            blz="50031000",
            bic="TRODDEF1XXX",
            name="Triodos Bank",
            city="Frankfurt",
            endpoint_url="https://example.com",
        )

        assert str(info) == "Triodos Bank (50031000)"


class TestFinTSInstituteDirectoryWithValidCsv:
    """Tests for FinTSInstituteDirectory with valid CSV data."""

    @pytest.fixture
    def valid_csv_content(self) -> str:
        """Create valid CSV content for testing."""
        return (
            "Nr.;BLZ;BIC;Institut;Ort;RZ;Organisation;HBCI-Zugang DNS;"
            "HBCI-Zugang IP;HBCI-Version;DDV;RDH-1;RDH-2;RDH-3;RDH-4;RDH-5;"
            "RDH-6;RDH-7;RDH-8;RDH-9;RDH-10;RAH-7;RAH-9;RAH-10;PIN/TAN-Zugang URL;"
            "Version;Datum\n"
            "1;50031000;TRODDEF1XXX;Triodos Bank Deutschland;Frankfurt am Main;"
            "Atruvia AG;BVR;fints2.atruvia.de;;3.0;;;;;;;;ja;;ja;ja;;;;"
            "https://fints2.atruvia.de/cgi-bin/hbciservlet;FinTS V3.0;06.09.2023\n"
            "2;10040000;COBADEBBXXX;Commerzbank;Berlin;eigenes Rechenzentrum;BdB;"
            "hbci.commerzbank.de;;3.0;;ja;ja;ja;;ja;;;ja;ja;ja;;ja;ja;"
            "https://fints.commerzbank.de/fints;FinTS V3.0;27.02.2024\n"
            "3;12030000;BYLADEM1001;Deutsche Kreditbank Berlin (DKB) AG;Berlin;"
            "eigenes Rechenzentrum;VÖB;;;;;;;;;;;;;;;;;;"
            "https://fints.dkb.de/fints;FinTS V3.0;30.10.2024\n"
        )

    @pytest.fixture
    def csv_file(self, valid_csv_content: str, tmp_path: Path) -> Path:
        """Create a temporary CSV file."""
        csv_path = tmp_path / "fints_institute.csv"
        csv_path.write_text(valid_csv_content, encoding="cp1252")
        return csv_path

    @pytest.fixture
    def directory(self, csv_file: Path) -> FinTSInstituteDirectory:
        """Create a directory instance with the test CSV."""
        return FinTSInstituteDirectory(csv_path=csv_file)

    def test_load_csv_successfully(self, directory: FinTSInstituteDirectory):
        """Should load CSV file successfully."""
        result = directory.load()

        assert result is True
        assert directory.is_loaded is True
        assert directory.load_error is None
        assert directory.institute_count == 3

    def test_find_by_blz_found(self, directory: FinTSInstituteDirectory):
        """Should find institute by BLZ."""
        info = directory.find_by_blz("50031000")

        assert info is not None
        assert info.blz == "50031000"
        assert info.bic == "TRODDEF1XXX"
        assert info.name == "Triodos Bank Deutschland"
        assert info.endpoint_url == "https://fints2.atruvia.de/cgi-bin/hbciservlet"

    def test_find_by_blz_not_found(self, directory: FinTSInstituteDirectory):
        """Should return None for unknown BLZ."""
        info = directory.find_by_blz("99999999")

        assert info is None

    def test_find_by_blz_normalizes_input(self, directory: FinTSInstituteDirectory):
        """Should normalize BLZ input (spaces)."""
        info = directory.find_by_blz("  50031000  ")

        assert info is not None
        assert info.blz == "50031000"

    def test_find_by_bic_found(self, directory: FinTSInstituteDirectory):
        """Should find institute by BIC."""
        info = directory.find_by_bic("COBADEBBXXX")

        assert info is not None
        assert info.blz == "10040000"
        assert info.name == "Commerzbank"

    def test_find_by_bic_normalizes_input(self, directory: FinTSInstituteDirectory):
        """Should normalize BIC input (case, spaces)."""
        info = directory.find_by_bic("  cobadebbxxx  ")

        assert info is not None
        assert info.bic == "COBADEBBXXX"

    def test_find_by_bic_not_found(self, directory: FinTSInstituteDirectory):
        """Should return None for unknown BIC."""
        info = directory.find_by_bic("UNKNOWNXXX")

        assert info is None

    def test_lazy_loading(self, directory: FinTSInstituteDirectory):
        """Should lazy load on first find_by_blz call."""
        assert directory.is_loaded is False

        # First call triggers loading
        directory.find_by_blz("50031000")

        assert directory.is_loaded is True

    def test_multiple_loads_are_idempotent(self, directory: FinTSInstituteDirectory):
        """Should only load once even if load() is called multiple times."""
        directory.load()
        count_after_first = directory.institute_count

        directory.load()  # Should be no-op
        count_after_second = directory.institute_count

        assert count_after_first == count_after_second


class TestFinTSInstituteDirectoryEdgeCases:
    """Tests for edge cases and error handling."""

    def test_file_not_found(self, tmp_path: Path):
        """Should handle missing CSV file gracefully."""
        directory = FinTSInstituteDirectory(
            csv_path=tmp_path / "nonexistent.csv",
        )

        result = directory.load()

        assert result is False
        assert directory.is_loaded is False
        assert isinstance(directory.load_error, CsvFileNotFoundError)

    def test_file_not_found_find_returns_none(self, tmp_path: Path):
        """Should return None on find when file doesn't exist."""
        directory = FinTSInstituteDirectory(
            csv_path=tmp_path / "nonexistent.csv",
        )

        info = directory.find_by_blz("50031000")

        assert info is None
        assert directory.is_loaded is False

    def test_empty_csv_file(self, tmp_path: Path):
        """Should handle empty CSV file."""
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("", encoding="cp1252")

        directory = FinTSInstituteDirectory(csv_path=csv_path)
        result = directory.load()

        assert result is False
        assert isinstance(directory.load_error, CsvParseError)

    def test_csv_with_only_header(self, tmp_path: Path):
        """Should handle CSV with only header row."""
        csv_path = tmp_path / "header_only.csv"
        csv_path.write_text(
            "Nr.;BLZ;BIC;Institut;Ort;etc\n",
            encoding="cp1252",
        )

        directory = FinTSInstituteDirectory(csv_path=csv_path)
        result = directory.load()

        assert result is False
        assert isinstance(directory.load_error, CsvParseError)

    def test_csv_with_invalid_rows(self, tmp_path: Path):
        """Should skip invalid rows but continue parsing."""
        csv_content = (
            "Nr.;BLZ;BIC;Institut;Ort;RZ;Org;DNS;IP;Ver;D;R1;R2;R3;R4;R5;R6;R7;R8;R9;R10;RA7;RA9;RA10;URL;V;D\n"
            "1;INVALID;XXX;Test1;City;;;;;;;;;;;;;;;;;;;;https://test1.com;;\n"  # Invalid BLZ
            "2;50031000;TRODDEF1XXX;Valid Bank;Frankfurt;;;;;;;;;;;;;;;;;;;;https://valid.com;;\n"  # Valid
            "3;12345678;XXX;No URL;City;;;;;;;;;;;;;;;;;;;;\n"  # No URL
        )
        csv_path = tmp_path / "mixed.csv"
        csv_path.write_text(csv_content, encoding="cp1252")

        directory = FinTSInstituteDirectory(csv_path=csv_path)
        result = directory.load()

        assert result is True
        assert directory.institute_count == 1  # Only the valid row
        assert directory.find_by_blz("50031000") is not None

    def test_csv_with_duplicate_blz(self, tmp_path: Path):
        """Should keep first occurrence of duplicate BLZ."""
        csv_content = (
            "Nr.;BLZ;BIC;Institut;Ort;RZ;Org;DNS;IP;Ver;D;R1;R2;R3;R4;R5;R6;R7;R8;R9;R10;RA7;RA9;RA10;URL;V;D\n"
            "1;50031000;BIC1;First Bank;City1;;;;;;;;;;;;;;;;;;;;https://first.com;;\n"
            "2;50031000;BIC2;Second Bank;City2;;;;;;;;;;;;;;;;;;;;https://second.com;;\n"
        )
        csv_path = tmp_path / "duplicates.csv"
        csv_path.write_text(csv_content, encoding="cp1252")

        directory = FinTSInstituteDirectory(csv_path=csv_path)
        directory.load()

        info = directory.find_by_blz("50031000")
        assert info is not None
        assert info.name == "First Bank"  # First occurrence kept

    def test_csv_with_short_rows(self, tmp_path: Path):
        """Should skip rows with insufficient columns."""
        csv_content = (
            "Nr.;BLZ;BIC;Institut;Ort;RZ;Org;DNS;IP;Ver;D;R1;R2;R3;R4;R5;R6;R7;R8;R9;R10;RA7;RA9;RA10;URL;V;D\n"
            "1;50031000;BIC;Short Row\n"  # Too few columns
            "2;12345678;VALIDBIC;Valid Bank;City;;;;;;;;;;;;;;;;;;;;https://valid.com;;\n"
        )
        csv_path = tmp_path / "short_rows.csv"
        csv_path.write_text(csv_content, encoding="cp1252")

        directory = FinTSInstituteDirectory(csv_path=csv_path)
        directory.load()

        assert directory.institute_count == 1
        assert directory.find_by_blz("12345678") is not None
        assert directory.find_by_blz("50031000") is None

    def test_custom_encoding(self, tmp_path: Path):
        """Should support custom encoding."""
        csv_content = (
            "Nr.;BLZ;BIC;Institut;Ort;RZ;Org;DNS;IP;Ver;D;R1;R2;R3;R4;R5;R6;R7;R8;R9;R10;RA7;RA9;RA10;URL;V;D\n"
            "1;50031000;BIC;Bank with Umlaut Ä;München;;;;;;;;;;;;;;;;;;;;https://test.com;;\n"
        )
        csv_path = tmp_path / "utf8.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        directory = FinTSInstituteDirectory(csv_path=csv_path, encoding="utf-8")
        directory.load()

        info = directory.find_by_blz("50031000")
        assert info is not None
        assert "Ä" in info.name
        assert info.city == "München"


class TestFinTSInstituteDirectoryWithRealCsv:
    """Integration tests with the real CSV file (if available)."""

    @pytest.fixture
    def real_directory(self) -> FinTSInstituteDirectory:
        """Create directory with the real CSV path."""
        return FinTSInstituteDirectory()

    @pytest.mark.skipif(
        not _REAL_CSV_PATH.exists(),
        reason="Real CSV file not available",
    )
    def test_load_real_csv(self, real_directory: FinTSInstituteDirectory):
        """Should load the real CSV file successfully."""
        result = real_directory.load()

        assert result is True
        assert real_directory.institute_count > 1000  # Should have many banks

    @pytest.mark.skipif(
        not _REAL_CSV_PATH.exists(),
        reason="Real CSV file not available",
    )
    def test_find_known_banks(self, real_directory: FinTSInstituteDirectory):
        """Should find known German banks."""
        # Triodos Bank
        triodos = real_directory.find_by_blz("50031000")
        assert triodos is not None
        assert "Triodos" in triodos.name
        assert triodos.endpoint_url.startswith("https://")

        # DKB
        dkb = real_directory.find_by_blz("12030000")
        assert dkb is not None
        assert "DKB" in dkb.name or "Kreditbank" in dkb.name

        # Commerzbank
        commerzbank = real_directory.find_by_blz("10040000")
        assert commerzbank is not None
        assert "Commerzbank" in commerzbank.name

