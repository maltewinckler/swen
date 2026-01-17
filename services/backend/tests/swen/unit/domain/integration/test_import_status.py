"""Tests for ImportStatus value object."""

from swen.domain.integration.value_objects import ImportStatus


class TestImportStatus:
    """Test cases for ImportStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses are defined."""
        assert ImportStatus.PENDING
        assert ImportStatus.SUCCESS
        assert ImportStatus.FAILED
        assert ImportStatus.DUPLICATE
        assert ImportStatus.SKIPPED

    def test_status_values(self):
        """Test status enum values."""
        assert ImportStatus.PENDING.value == "pending"
        assert ImportStatus.SUCCESS.value == "success"
        assert ImportStatus.FAILED.value == "failed"
        assert ImportStatus.DUPLICATE.value == "duplicate"
        assert ImportStatus.SKIPPED.value == "skipped"

    def test_is_final_for_success(self):
        """Test SUCCESS is a final status."""
        assert ImportStatus.SUCCESS.is_final() is True

    def test_is_final_for_duplicate(self):
        """Test DUPLICATE is a final status."""
        assert ImportStatus.DUPLICATE.is_final() is True

    def test_is_final_for_pending(self):
        """Test PENDING is not a final status."""
        assert ImportStatus.PENDING.is_final() is False

    def test_is_final_for_failed(self):
        """Test FAILED is not a final status."""
        assert ImportStatus.FAILED.is_final() is False

    def test_is_final_for_skipped(self):
        """Test SKIPPED is not a final status."""
        assert ImportStatus.SKIPPED.is_final() is False

    def test_is_error_for_failed(self):
        """Test FAILED is an error status."""
        assert ImportStatus.FAILED.is_error() is True

    def test_is_error_for_success(self):
        """Test SUCCESS is not an error status."""
        assert ImportStatus.SUCCESS.is_error() is False

    def test_is_error_for_pending(self):
        """Test PENDING is not an error status."""
        assert ImportStatus.PENDING.is_error() is False

    def test_is_error_for_duplicate(self):
        """Test DUPLICATE is not an error status."""
        assert ImportStatus.DUPLICATE.is_error() is False

    def test_is_error_for_skipped(self):
        """Test SKIPPED is not an error status."""
        assert ImportStatus.SKIPPED.is_error() is False

    def test_can_retry_for_failed(self):
        """Test FAILED status can be retried."""
        assert ImportStatus.FAILED.can_retry() is True

    def test_can_retry_for_skipped(self):
        """Test SKIPPED status can be retried."""
        assert ImportStatus.SKIPPED.can_retry() is True

    def test_can_retry_for_pending(self):
        """Test PENDING status cannot be retried."""
        assert ImportStatus.PENDING.can_retry() is False

    def test_can_retry_for_success(self):
        """Test SUCCESS status cannot be retried."""
        assert ImportStatus.SUCCESS.can_retry() is False

    def test_can_retry_for_duplicate(self):
        """Test DUPLICATE status cannot be retried."""
        assert ImportStatus.DUPLICATE.can_retry() is False

    def test_status_equality(self):
        """Test status equality comparison."""
        assert ImportStatus.PENDING == ImportStatus.PENDING
        assert ImportStatus.SUCCESS == ImportStatus.SUCCESS
        assert ImportStatus.PENDING != ImportStatus.SUCCESS

    def test_status_in_list(self):
        """Test status can be checked in list."""
        final_statuses = [ImportStatus.SUCCESS, ImportStatus.DUPLICATE]

        assert ImportStatus.SUCCESS in final_statuses
        assert ImportStatus.DUPLICATE in final_statuses
        assert ImportStatus.PENDING not in final_statuses

    def test_all_statuses_coverage(self):
        """Test that all statuses are covered by is_final, is_error, or can_retry."""
        all_statuses = [
            ImportStatus.PENDING,
            ImportStatus.SUCCESS,
            ImportStatus.FAILED,
            ImportStatus.DUPLICATE,
            ImportStatus.SKIPPED,
        ]

        for status in all_statuses:
            # Each status should have defined behavior for these methods
            assert isinstance(status.is_final(), bool)
            assert isinstance(status.is_error(), bool)
            assert isinstance(status.can_retry(), bool)

    def test_logical_consistency_final_and_retry(self):
        """Test that final statuses cannot be retried."""
        all_statuses = [
            ImportStatus.PENDING,
            ImportStatus.SUCCESS,
            ImportStatus.FAILED,
            ImportStatus.DUPLICATE,
            ImportStatus.SKIPPED,
        ]

        for status in all_statuses:
            if status.is_final():
                # Final statuses should not be retryable
                assert status.can_retry() is False

    def test_logical_consistency_error_and_retry(self):
        """Test that error statuses can be retried."""
        if ImportStatus.FAILED.is_error():
            assert ImportStatus.FAILED.can_retry() is True
