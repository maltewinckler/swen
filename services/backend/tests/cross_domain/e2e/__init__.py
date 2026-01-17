"""End-to-end tests for critical user journeys.

E2E tests simulate complete user flows through the API, testing
realistic scenarios that span multiple endpoints. These tests
use a real PostgreSQL database via Testcontainers.

Test categories:
- User Onboarding: Register → Init Chart → First Transaction
- Account Management: Create → Update → Deactivate → Reactivate
- Transaction Lifecycle: Create → Post → Edit → Unpost → Delete
- Dashboard & Reporting: View Summary → Spending → Balances
- Preferences Management: Get → Update → Reset
- Multi-User Isolation: Verify data isolation between users

Run with: pytest tests/cross_domain/e2e -m e2e -v
"""
