from dataclasses import dataclass
from typing import cast

from passlib.context import CryptContext  # type: ignore[import-untyped]


@dataclass
class HashService:
    pwd_context: CryptContext

    def hash_password(self, password: str) -> str:
        return cast(str, self.pwd_context.hash(password))

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return cast(bool, self.pwd_context.verify(plain_password, hashed_password))


def create_hash_service() -> HashService:
    return HashService(CryptContext(schemes=["argon2"], deprecated="auto"))
