"""User credential aggregate.

Holds a user's password hash and login-lockout state. Kept as its own
aggregate (identity borrowed from ``User`` via ``user_id``) rather than
folded into ``User``. No invariant spans both, and every login attempt
would otherwise churn the identity aggregate for a concern that has
nothing to do with identity.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCredential(BaseModel):
    """Immutable credential data returned by repository.

    This is a pure data transfer object that decouples the domain
    from persistence implementation details.
    """

    model_config = ConfigDict(frozen=True)

    user_id: str
    password_hash: str
    failed_login_attempts: int
    locked_until: datetime | None
    last_login_at: datetime | None
