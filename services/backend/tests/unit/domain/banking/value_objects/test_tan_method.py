"""Unit tests for TANMethod value object."""

import pytest

from swen.domain.banking.value_objects import TANMethod, TANMethodType


class TestTANMethodType:
    """Tests for TANMethodType enum."""

    def test_all_types_exist(self):
        """Verify all expected TAN method types exist."""
        expected_types = [
            "decoupled",
            "push",
            "sms",
            "chiptan",
            "photo_tan",
            "manual",
            "unknown",
        ]

        for type_name in expected_types:
            assert hasattr(TANMethodType, type_name.upper())
            assert TANMethodType(type_name).value == type_name

    def test_type_values(self):
        """Verify enum values match expected strings."""
        assert TANMethodType.DECOUPLED.value == "decoupled"
        assert TANMethodType.PUSH.value == "push"
        assert TANMethodType.SMS.value == "sms"
        assert TANMethodType.CHIPTAN.value == "chiptan"
        assert TANMethodType.PHOTO_TAN.value == "photo_tan"
        assert TANMethodType.MANUAL.value == "manual"
        assert TANMethodType.UNKNOWN.value == "unknown"


class TestTANMethodCreation:
    """Tests for TANMethod creation and validation."""

    def test_create_minimal_tan_method(self):
        """Create TANMethod with only required fields."""
        method = TANMethod(
            code="946",
            name="SecureGo plus",
        )

        assert method.code == "946"
        assert method.name == "SecureGo plus"
        assert method.method_type == TANMethodType.UNKNOWN
        assert method.is_decoupled is False

    def test_create_full_tan_method(self):
        """Create TANMethod with all fields."""
        method = TANMethod(
            code="940",
            name="DKB App",
            method_type=TANMethodType.DECOUPLED,
            is_decoupled=True,
            technical_id="SealOne",
            zka_id="Decoupled",
            zka_version="1.0",
            max_tan_length=6,
            decoupled_max_polls=999,
            decoupled_first_poll_delay=5,
            decoupled_poll_interval=2,
            supports_cancel=True,
            supports_multiple_tan=False,
        )

        assert method.code == "940"
        assert method.name == "DKB App"
        assert method.method_type == TANMethodType.DECOUPLED
        assert method.is_decoupled is True
        assert method.technical_id == "SealOne"
        assert method.zka_id == "Decoupled"
        assert method.zka_version == "1.0"
        assert method.max_tan_length == 6
        assert method.decoupled_max_polls == 999
        assert method.decoupled_first_poll_delay == 5
        assert method.decoupled_poll_interval == 2
        assert method.supports_cancel is True
        assert method.supports_multiple_tan is False

    def test_create_chiptan_method(self):
        """Create a chipTAN method."""
        method = TANMethod(
            code="972",
            name="chipTAN optical",
            method_type=TANMethodType.CHIPTAN,
            is_decoupled=False,
            technical_id="HHD1.4",
        )

        assert method.code == "972"
        assert method.method_type == TANMethodType.CHIPTAN
        assert method.is_decoupled is False
        assert method.technical_id == "HHD1.4"

    def test_create_sms_tan_method(self):
        """Create an SMS TAN method."""
        method = TANMethod(
            code="920",
            name="smsTAN",
            method_type=TANMethodType.SMS,
            is_decoupled=False,
            max_tan_length=6,
        )

        assert method.code == "920"
        assert method.method_type == TANMethodType.SMS
        assert method.max_tan_length == 6


class TestTANMethodImmutability:
    """Tests for TANMethod immutability."""

    def test_tan_method_is_frozen(self):
        """TANMethod should be immutable (frozen)."""
        method = TANMethod(code="946", name="SecureGo plus")

        with pytest.raises(Exception):  # ValidationError for frozen model
            method.code = "999"

    def test_tan_method_hashable(self):
        """TANMethod should be hashable (can be used in sets)."""
        method1 = TANMethod(code="946", name="SecureGo plus")
        method2 = TANMethod(code="946", name="SecureGo plus")

        # Same content should be equal
        assert method1 == method2

        # Should be usable in sets
        method_set = {method1, method2}  # type: ignore[misc]
        assert len(method_set) == 1


class TestTANMethodProperties:
    """Tests for TANMethod computed properties."""

    def test_is_interactive_for_decoupled(self):
        """Decoupled method is not interactive (no TAN entry)."""
        method = TANMethod(
            code="940",
            name="DKB App",
            is_decoupled=True,
        )

        assert method.is_interactive is False

    def test_is_interactive_for_chiptan(self):
        """chipTAN is interactive (requires TAN entry)."""
        method = TANMethod(
            code="972",
            name="chipTAN optical",
            is_decoupled=False,
        )

        assert method.is_interactive is True

    def test_is_interactive_for_sms(self):
        """SMS TAN is interactive."""
        method = TANMethod(
            code="920",
            name="smsTAN",
            is_decoupled=False,
        )

        assert method.is_interactive is True


class TestTANMethodStringRepresentation:
    """Tests for TANMethod string output."""

    def test_str_basic(self):
        """Test basic string representation."""
        method = TANMethod(
            code="972",
            name="chipTAN optical",
            is_decoupled=False,
        )

        result = str(method)
        assert "972" in result
        assert "chipTAN optical" in result

    def test_str_decoupled(self):
        """Test string representation for decoupled method."""
        method = TANMethod(
            code="940",
            name="DKB App",
            is_decoupled=True,
        )

        result = str(method)
        assert "940" in result
        assert "DKB App" in result
        assert "app-based" in result.lower()


class TestTANMethodRealWorldExamples:
    """Tests with real-world TAN method examples."""

    def test_dkb_app(self):
        """Test DKB App TAN method."""
        method = TANMethod(
            code="940",
            name="DKB-App",
            method_type=TANMethodType.DECOUPLED,
            is_decoupled=True,
            technical_id="SealOne",
            decoupled_max_polls=999,
            decoupled_first_poll_delay=5,
            decoupled_poll_interval=2,
        )

        assert method.is_decoupled is True
        assert method.is_interactive is False
        assert method.decoupled_max_polls == 999

    def test_securego_plus(self):
        """Test SecureGo plus (Sparkasse) method."""
        method = TANMethod(
            code="946",
            name="SecureGo plus",
            method_type=TANMethodType.DECOUPLED,
            is_decoupled=True,
            technical_id="DECOUPLED",
        )

        assert method.code == "946"
        assert method.is_decoupled is True

    def test_chiptan_optical(self):
        """Test chipTAN optical method."""
        method = TANMethod(
            code="972",
            name="chipTAN optisch",
            method_type=TANMethodType.CHIPTAN,
            is_decoupled=False,
            technical_id="HHD1.4",
            max_tan_length=6,
        )

        assert method.code == "972"
        assert method.is_decoupled is False
        assert method.max_tan_length == 6

    def test_photo_tan(self):
        """Test photoTAN method."""
        method = TANMethod(
            code="982",
            name="photoTAN",
            method_type=TANMethodType.PHOTO_TAN,
            is_decoupled=False,
        )

        assert method.code == "982"
        assert method.method_type == TANMethodType.PHOTO_TAN


class TestTANMethodSerialization:
    """Tests for TANMethod serialization."""

    def test_to_dict(self):
        """TANMethod should serialize to dict correctly."""
        method = TANMethod(
            code="940",
            name="DKB App",
            method_type=TANMethodType.DECOUPLED,
            is_decoupled=True,
        )

        data = method.model_dump()

        assert data["code"] == "940"
        assert data["name"] == "DKB App"
        assert data["method_type"] == "decoupled"
        assert data["is_decoupled"] is True

    def test_from_dict(self):
        """TANMethod should deserialize from dict correctly."""
        data = {
            "code": "940",
            "name": "DKB App",
            "method_type": "decoupled",
            "is_decoupled": True,
        }

        method = TANMethod.model_validate(data)

        assert method.code == "940"
        assert method.name == "DKB App"
        assert method.method_type == TANMethodType.DECOUPLED
        assert method.is_decoupled is True
