"""External service tests (real bank connections).

These tests connect to real third-party systems and require:
- Real bank credentials (FINTS_BLZ, FINTS_USERNAME, etc.)
- Network access
- Sometimes manual TAN approval

Run with: pytest tests/external/ --run-external
"""
