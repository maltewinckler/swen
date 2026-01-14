"""Unit tests for QueryTanMethodsQuery."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from swen.application.queries import (
    QueryTanMethodsQuery,
    TANMethodInfo,
    TANMethodsResult,
)
from swen.domain.banking.value_objects import BankCredentials, TANMethod, TANMethodType


class TestQueryTanMethodsQuery:
    """Tests for the QueryTanMethodsQuery."""

    @pytest.fixture
    def mock_bank_adapter(self):
        """Create a mock bank connection adapter."""
        return AsyncMock()

    @pytest.fixture
    def sample_credentials(self):
        """Create sample bank credentials for testing."""
        return BankCredentials.from_plain(
            blz="12345678",
            username="testuser",
            pin="testpin",
            endpoint="https://bank.example.com/fints",
        )

    @pytest.fixture
    def sample_tan_methods(self):
        """Create sample TAN methods."""
        return [
            TANMethod(
                code="940",
                name="DKB App",
                method_type=TANMethodType.DECOUPLED,
                is_decoupled=True,
                technical_id="SealOne",
                decoupled_max_polls=999,
                decoupled_first_poll_delay=5,
                decoupled_poll_interval=2,
            ),
            TANMethod(
                code="972",
                name="chipTAN optical",
                method_type=TANMethodType.CHIPTAN,
                is_decoupled=False,
                technical_id="HHD1.4",
                max_tan_length=6,
            ),
        ]

    @pytest.mark.asyncio
    async def test_execute_returns_tan_methods(
        self, mock_bank_adapter, sample_credentials, sample_tan_methods,
    ):
        """Test that execute returns discovered TAN methods."""
        mock_bank_adapter.get_tan_methods.return_value = sample_tan_methods

        query = QueryTanMethodsQuery(mock_bank_adapter)
        result = await query.execute(sample_credentials, "Test Bank")

        assert isinstance(result, TANMethodsResult)
        assert result.blz == "12345678"
        assert result.bank_name == "Test Bank"
        assert len(result.tan_methods) == 2

        # Verify first method
        method1 = result.tan_methods[0]
        assert method1.code == "940"
        assert method1.name == "DKB App"
        assert method1.method_type == "decoupled"
        assert method1.is_decoupled is True

        # Verify adapter was called with correct credentials
        mock_bank_adapter.get_tan_methods.assert_called_once_with(sample_credentials)

    @pytest.mark.asyncio
    async def test_execute_returns_empty_list_when_no_methods(
        self, mock_bank_adapter, sample_credentials,
    ):
        """Test that execute handles banks with no TAN methods."""
        mock_bank_adapter.get_tan_methods.return_value = []

        query = QueryTanMethodsQuery(mock_bank_adapter)
        result = await query.execute(sample_credentials, "Test Bank")

        assert result.tan_methods == []
        assert result.default_method is None

    @pytest.mark.asyncio
    async def test_execute_selects_decoupled_as_default(
        self, mock_bank_adapter, sample_credentials, sample_tan_methods,
    ):
        """Test that decoupled method is selected as default."""
        mock_bank_adapter.get_tan_methods.return_value = sample_tan_methods

        query = QueryTanMethodsQuery(mock_bank_adapter)
        result = await query.execute(sample_credentials, "Test Bank")

        # First decoupled method (940) should be default
        assert result.default_method == "940"

    @pytest.mark.asyncio
    async def test_execute_selects_first_method_if_no_decoupled(
        self, mock_bank_adapter, sample_credentials,
    ):
        """Test fallback to first method when no decoupled available."""
        non_decoupled_methods = [
            TANMethod(
                code="972",
                name="chipTAN optical",
                method_type=TANMethodType.CHIPTAN,
                is_decoupled=False,
            ),
            TANMethod(
                code="920",
                name="smsTAN",
                method_type=TANMethodType.SMS,
                is_decoupled=False,
            ),
        ]
        mock_bank_adapter.get_tan_methods.return_value = non_decoupled_methods

        query = QueryTanMethodsQuery(mock_bank_adapter)
        result = await query.execute(sample_credentials, "Test Bank")

        # First method should be default
        assert result.default_method == "972"

    @pytest.mark.asyncio
    async def test_execute_propagates_adapter_exception(
        self, mock_bank_adapter, sample_credentials,
    ):
        """Test that adapter exceptions are propagated."""
        mock_bank_adapter.get_tan_methods.side_effect = Exception("Connection failed")

        query = QueryTanMethodsQuery(mock_bank_adapter)

        with pytest.raises(Exception, match="Connection failed"):
            await query.execute(sample_credentials, "Test Bank")


class TestTANMethodInfo:
    """Tests for TANMethodInfo dataclass."""

    def test_from_domain_creates_correct_dto(self):
        """Test conversion from domain TANMethod to DTO."""
        domain_method = TANMethod(
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

        info = TANMethodInfo.from_domain(domain_method)

        assert info.code == "940"
        assert info.name == "DKB App"
        assert info.method_type == "decoupled"
        assert info.is_decoupled is True
        assert info.technical_id == "SealOne"
        assert info.zka_id == "Decoupled"
        assert info.zka_version == "1.0"
        assert info.max_tan_length == 6
        assert info.decoupled_max_polls == 999
        assert info.decoupled_first_poll_delay == 5
        assert info.decoupled_poll_interval == 2
        assert info.supports_cancel is True
        assert info.supports_multiple_tan is False

    def test_from_domain_handles_none_values(self):
        """Test conversion handles None optional fields."""
        domain_method = TANMethod(
            code="920",
            name="smsTAN",
            method_type=TANMethodType.SMS,
            is_decoupled=False,
        )

        info = TANMethodInfo.from_domain(domain_method)

        assert info.code == "920"
        assert info.technical_id is None
        assert info.zka_id is None
        assert info.max_tan_length is None
        assert info.decoupled_max_polls is None


class TestTANMethodsResult:
    """Tests for TANMethodsResult dataclass."""

    def test_result_creation(self):
        """Test TANMethodsResult creation."""
        methods = [
            TANMethodInfo(
                code="940",
                name="DKB App",
                method_type="decoupled",
                is_decoupled=True,
            ),
        ]

        result = TANMethodsResult(
            blz="12345678",
            bank_name="Test Bank",
            tan_methods=methods,
            default_method="940",
        )

        assert result.blz == "12345678"
        assert result.bank_name == "Test Bank"
        assert len(result.tan_methods) == 1
        assert result.default_method == "940"

    def test_result_with_no_default(self):
        """Test TANMethodsResult with no default method."""
        result = TANMethodsResult(
            blz="12345678",
            bank_name="Test Bank",
            tan_methods=[],
            default_method=None,
        )

        assert result.default_method is None


class TestQueryTanMethodsQueryDependencyInjection:
    """Tests for proper dependency injection."""

    def test_query_accepts_bank_adapter(self):
        """Test that query accepts a bank connection adapter."""
        mock_adapter = AsyncMock()
        query = QueryTanMethodsQuery(mock_adapter)
        assert query._adapter is mock_adapter

    def test_from_factory_creates_query(self):
        """Test that from_factory creates a configured query."""
        mock_factory = MagicMock()

        # from_factory should create query with GeldstromAdapter
        query = QueryTanMethodsQuery.from_factory(mock_factory)

        assert isinstance(query, QueryTanMethodsQuery)
        # Adapter should be a GeldstromAdapter (imported locally in from_factory)
        from swen.infrastructure.banking.geldstrom_adapter import GeldstromAdapter

        assert isinstance(query._adapter, GeldstromAdapter)

