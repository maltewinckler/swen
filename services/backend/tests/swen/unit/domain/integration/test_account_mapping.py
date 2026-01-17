"""Tests for AccountMapping entity."""

from uuid import UUID, uuid4

import pytest

from swen.domain.integration.entities import AccountMapping

# Test user ID for all tests in this module
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


class TestAccountMapping:
    """Test cases for AccountMapping entity."""

    def test_account_mapping_creation(self):
        """Test creating a basic AccountMapping instance."""
        iban = "DE89370400440532013000"
        accounting_account_id = uuid4()
        account_name = "DKB Checking Account"

        mapping = AccountMapping(
            iban=iban,
            accounting_account_id=accounting_account_id,
            account_name=account_name,
            user_id=TEST_USER_ID,
        )

        assert mapping.iban == iban
        assert mapping.accounting_account_id == accounting_account_id
        assert mapping.account_name == account_name
        assert mapping.is_active is True
        assert isinstance(mapping.id, UUID)
        assert mapping.created_at is not None
        assert mapping.updated_at is not None

    def test_account_mapping_iban_normalization(self):
        """Test IBAN is normalized to uppercase and trimmed."""
        iban_with_spaces = "  de89 3704 0044 0532 0130 00  "
        accounting_account_id = uuid4()

        mapping = AccountMapping(
            iban=iban_with_spaces,
            accounting_account_id=accounting_account_id,
            account_name="Test Account",
            user_id=TEST_USER_ID,
        )

        assert mapping.iban == "DE89370400440532013000"

    def test_account_mapping_name_normalization(self):
        """Test account name is trimmed."""
        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=uuid4(),
            account_name="  Test Account  ",
            user_id=TEST_USER_ID,
        )

        assert mapping.account_name == "Test Account"

    def test_account_mapping_deterministic_id(self):
        """Test that same IBAN and account ID always produce same mapping ID."""
        iban = "DE89370400440532013000"
        accounting_account_id = uuid4()

        mapping1 = AccountMapping(
            iban=iban,
            accounting_account_id=accounting_account_id,
            account_name="First Mapping",
            user_id=TEST_USER_ID,
        )

        mapping2 = AccountMapping(
            iban=iban,
            accounting_account_id=accounting_account_id,
            account_name="Second Mapping",  # Different name shouldn't matter
            user_id=TEST_USER_ID,
        )

        # Should have the same ID since IBAN and accounting_account_id match
        assert mapping1.id == mapping2.id

    def test_account_mapping_different_iban_different_id(self):
        """Test different IBANs produce different mapping IDs."""
        accounting_account_id = uuid4()

        mapping1 = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=accounting_account_id,
            account_name="Account 1",
            user_id=TEST_USER_ID,
        )

        mapping2 = AccountMapping(
            iban="DE89370400440532013001",
            accounting_account_id=accounting_account_id,
            account_name="Account 2",
            user_id=TEST_USER_ID,
        )

        assert mapping1.id != mapping2.id

    def test_account_mapping_different_accounting_account_different_id(self):
        """Test different accounting accounts produce different mapping IDs."""
        iban = "DE89370400440532013000"

        mapping1 = AccountMapping(
            iban=iban,
            accounting_account_id=uuid4(),
            account_name="Account 1",
            user_id=TEST_USER_ID,
        )

        mapping2 = AccountMapping(
            iban=iban,
            accounting_account_id=uuid4(),
            account_name="Account 2",
            user_id=TEST_USER_ID,
        )

        assert mapping1.id != mapping2.id

    def test_account_mapping_with_inactive_status(self):
        """Test creating an inactive mapping."""
        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=uuid4(),
            account_name="Test Account",
            user_id=TEST_USER_ID,
            is_active=False,
        )

        assert mapping.is_active is False

    def test_account_mapping_empty_iban_raises_error(self):
        """Test that empty IBAN raises ValueError."""
        with pytest.raises(ValueError, match="IBAN cannot be empty"):
            AccountMapping(
                iban="",
                accounting_account_id=uuid4(),
                account_name="Test Account",
                user_id=TEST_USER_ID,
            )

        with pytest.raises(ValueError, match="IBAN cannot be empty"):
            AccountMapping(
                iban="   ",
                accounting_account_id=uuid4(),
                account_name="Test Account",
                user_id=TEST_USER_ID,
            )

    def test_account_mapping_invalid_iban_length_raises_error(self):
        """Test that IBAN with invalid length raises ValueError."""
        # Too short (< 15 characters)
        with pytest.raises(ValueError, match="Invalid IBAN length"):
            AccountMapping(
                iban="DE1234567890",  # Only 12 characters
                accounting_account_id=uuid4(),
                account_name="Test Account",
                user_id=TEST_USER_ID,
            )

        # Too long (> 34 characters)
        with pytest.raises(ValueError, match="Invalid IBAN length"):
            AccountMapping(
                iban="DE" + "1" * 40,  # 42 characters
                accounting_account_id=uuid4(),
                account_name="Test Account",
                user_id=TEST_USER_ID,
            )

    def test_account_mapping_invalid_iban_country_code_raises_error(self):
        """Test that IBAN not starting with 2 letters raises ValueError."""
        with pytest.raises(
            ValueError,
            match="IBAN must start with 2 letter country code",
        ):
            AccountMapping(
                iban="1289370400440532013000",  # Starts with number
                accounting_account_id=uuid4(),
                account_name="Test Account",
                user_id=TEST_USER_ID,
            )

    def test_account_mapping_empty_name_raises_error(self):
        """Test that empty account name raises ValueError."""
        with pytest.raises(ValueError, match="Account name cannot be empty"):
            AccountMapping(
                iban="DE89370400440532013000",
                accounting_account_id=uuid4(),
                account_name="",
                user_id=TEST_USER_ID,
            )

        with pytest.raises(ValueError, match="Account name cannot be empty"):
            AccountMapping(
                iban="DE89370400440532013000",
                accounting_account_id=uuid4(),
                account_name="   ",
                user_id=TEST_USER_ID,
            )

    def test_update_account_name(self):
        """Test updating account name."""
        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=uuid4(),
            account_name="Old Name",
            user_id=TEST_USER_ID,
        )

        original_updated_at = mapping.updated_at

        mapping.update_account_name("New Name")

        assert mapping.account_name == "New Name"
        assert mapping.updated_at > original_updated_at

    def test_update_account_name_with_whitespace(self):
        """Test updating account name strips whitespace."""
        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=uuid4(),
            account_name="Old Name",
            user_id=TEST_USER_ID,
        )

        mapping.update_account_name("  New Name  ")

        assert mapping.account_name == "New Name"

    def test_update_account_name_empty_raises_error(self):
        """Test updating account name to empty string raises ValueError."""
        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=uuid4(),
            account_name="Old Name",
            user_id=TEST_USER_ID,
        )

        with pytest.raises(ValueError, match="Account name cannot be empty"):
            mapping.update_account_name("")

        with pytest.raises(ValueError, match="Account name cannot be empty"):
            mapping.update_account_name("   ")

    def test_deactivate_mapping(self):
        """Test deactivating a mapping."""
        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=uuid4(),
            account_name="Test Account",
            user_id=TEST_USER_ID,
        )

        assert mapping.is_active is True
        original_updated_at = mapping.updated_at

        mapping.deactivate()

        assert mapping.is_active is False
        assert mapping.updated_at > original_updated_at

    def test_activate_mapping(self):
        """Test activating a mapping."""
        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=uuid4(),
            account_name="Test Account",
            user_id=TEST_USER_ID,
            is_active=False,
        )

        assert mapping.is_active is False
        original_updated_at = mapping.updated_at

        mapping.activate()

        assert mapping.is_active is True
        assert mapping.updated_at > original_updated_at

    def test_update_accounting_account(self):
        """Test updating the accounting account ID."""
        iban = "DE89370400440532013000"
        old_account_id = uuid4()
        new_account_id = uuid4()

        mapping = AccountMapping(
            iban=iban,
            accounting_account_id=old_account_id,
            account_name="Test Account",
            user_id=TEST_USER_ID,
        )

        original_id = mapping.id
        original_updated_at = mapping.updated_at

        mapping.update_accounting_account(new_account_id)

        assert mapping.accounting_account_id == new_account_id
        assert mapping.updated_at > original_updated_at
        # ID should change since it's based on IBAN + accounting_account_id
        assert mapping.id != original_id

        # Verify new ID is deterministic
        new_mapping = AccountMapping(
            iban=iban,
            accounting_account_id=new_account_id,
            account_name="Test Account",
            user_id=TEST_USER_ID,
        )
        assert mapping.id == new_mapping.id

    def test_equality(self):
        """Test equality comparison based on ID."""
        iban = "DE89370400440532013000"
        accounting_account_id = uuid4()

        mapping1 = AccountMapping(
            iban=iban,
            accounting_account_id=accounting_account_id,
            account_name="Account 1",
            user_id=TEST_USER_ID,
        )

        mapping2 = AccountMapping(
            iban=iban,
            accounting_account_id=accounting_account_id,
            account_name="Account 2",
            user_id=TEST_USER_ID,
        )

        # Same IBAN and accounting_account_id = same ID = equal
        assert mapping1 == mapping2

    def test_inequality(self):
        """Test inequality comparison."""
        mapping1 = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=uuid4(),
            account_name="Account 1",
            user_id=TEST_USER_ID,
        )

        mapping2 = AccountMapping(
            iban="DE89370400440532013001",
            accounting_account_id=uuid4(),
            account_name="Account 2",
            user_id=TEST_USER_ID,
        )

        assert mapping1 != mapping2

    def test_equality_with_non_account_mapping(self):
        """Test equality comparison with non-AccountMapping object."""
        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=uuid4(),
            account_name="Test Account",
            user_id=TEST_USER_ID,
        )

        assert mapping != "not a mapping"
        assert mapping != 123
        assert mapping is not None

    def test_hashable(self):
        """Test AccountMapping can be used in sets and as dict keys."""
        mapping1 = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=uuid4(),
            account_name="Account 1",
            user_id=TEST_USER_ID,
        )

        mapping2 = AccountMapping(
            iban="DE89370400440532013001",
            accounting_account_id=uuid4(),
            account_name="Account 2",
            user_id=TEST_USER_ID,
        )

        # Can be added to set
        mapping_set = {mapping1, mapping2}
        assert len(mapping_set) == 2

        # Can be used as dict key
        mapping_dict = {mapping1: "value1", mapping2: "value2"}
        assert mapping_dict[mapping1] == "value1"

    def test_string_representation(self):
        """Test string representation of AccountMapping."""
        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=uuid4(),
            account_name="DKB Checking",
            user_id=TEST_USER_ID,
        )

        str_repr = str(mapping)

        assert "AccountMapping" in str_repr
        assert "ACTIVE" in str_repr
        assert "DKB Checking" in str_repr
        assert "DE89370400440532013000" in str_repr

    def test_string_representation_inactive(self):
        """Test string representation of inactive AccountMapping."""
        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=uuid4(),
            account_name="DKB Checking",
            user_id=TEST_USER_ID,
            is_active=False,
        )

        str_repr = str(mapping)

        assert "INACTIVE" in str_repr

    def test_various_valid_iban_formats(self):
        """Test various valid IBAN formats."""
        valid_ibans = [
            "DE89370400440532013000",  # German IBAN (22 chars)
            "GB29NWBK60161331926819",  # UK IBAN (22 chars)
            "FR1420041010050500013M02606",  # French IBAN (27 chars)
            "IT60X0542811101000000123456",  # Italian IBAN (27 chars)
            "ES9121000418450200051332",  # Spanish IBAN (24 chars)
        ]

        for iban in valid_ibans:
            mapping = AccountMapping(
                iban=iban,
                accounting_account_id=uuid4(),
                account_name="Test Account",
                user_id=TEST_USER_ID,
            )
            assert mapping.iban == iban.upper()

    def test_iban_case_insensitive_for_deterministic_id(self):
        """Test that IBAN case doesn't affect deterministic ID."""
        accounting_account_id = uuid4()

        mapping1 = AccountMapping(
            iban="de89370400440532013000",  # lowercase
            accounting_account_id=accounting_account_id,
            account_name="Account 1",
            user_id=TEST_USER_ID,
        )

        mapping2 = AccountMapping(
            iban="DE89370400440532013000",  # uppercase
            accounting_account_id=accounting_account_id,
            account_name="Account 2",
            user_id=TEST_USER_ID,
        )

        # Should have same ID since IBAN is normalized
        assert mapping1.id == mapping2.id
        assert mapping1.iban == mapping2.iban == "DE89370400440532013000"
