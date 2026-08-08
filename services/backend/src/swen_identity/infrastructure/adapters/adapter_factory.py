"""Default implementation of swen_identity's AdapterFactory Protocol."""

from __future__ import annotations

from swen_identity.application.factories.adapter_factory import AdapterFactory
from swen_identity.infrastructure.adapters.bcrypt_password_hashing_adapter import (
    BcryptPasswordHashingAdapter,
)
from swen_identity.infrastructure.adapters.jwt_token_handling_adapter import (
    JWTTokenHandlingAdapter,
)


class AdapterFactoryDefault(AdapterFactory):
    """Builds the JWT/bcrypt-backed adapters for swen_identity's ports."""

    def __init__(
        self,
        jwt_secret_key: str,
        jwt_access_token_expire_hours: int,
        jwt_refresh_token_expire_days: int,
        bcrypt_rounds: int = 12,
    ) -> None:
        self._jwt_secret_key = jwt_secret_key
        self._jwt_access_token_expire_hours = jwt_access_token_expire_hours
        self._jwt_refresh_token_expire_days = jwt_refresh_token_expire_days
        self._bcrypt_rounds = bcrypt_rounds

    def token_handling_port(self) -> JWTTokenHandlingAdapter:
        return JWTTokenHandlingAdapter(
            secret_key=self._jwt_secret_key,
            access_token_expire_hours=self._jwt_access_token_expire_hours,
            refresh_token_expire_days=self._jwt_refresh_token_expire_days,
        )

    def password_hashing_port(self) -> BcryptPasswordHashingAdapter:
        return BcryptPasswordHashingAdapter(rounds=self._bcrypt_rounds)
