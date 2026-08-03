import base64
import binascii
import secrets
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CredentialConfigurationError(RuntimeError):
    """The configured key ring cannot encrypt marketplace credentials."""


class CredentialDecryptionError(RuntimeError):
    """Credential authentication failed without exposing encrypted material."""


@dataclass(frozen=True)
class EncryptedCredential:
    value: bytes
    key_version: int
    masked_hint: str


@dataclass(frozen=True)
class CredentialCipher:
    encoded_keys: dict[int, str]
    active_key_version: int

    def _key(self, version: int) -> bytes:
        encoded = self.encoded_keys.get(version)
        if encoded is None:
            raise CredentialConfigurationError(f"Credential key version {version} is not configured")
        try:
            key = base64.urlsafe_b64decode(encoded.encode("ascii"))
        except (ValueError, binascii.Error) as exc:
            raise CredentialConfigurationError("Credential key is not valid URL-safe base64") from exc
        if len(key) != 32:
            raise CredentialConfigurationError("Credential key must decode to exactly 32 bytes")
        return key

    @staticmethod
    def mask(secret: str) -> str:
        if len(secret) < 8:
            return "****"
        return f"{secret[:2]}…{secret[-4:]}"

    def encrypt(self, secret: str, *, cabinet_id: str) -> EncryptedCredential:
        if not secret:
            raise ValueError("Marketplace credential must not be empty")
        nonce = secrets.token_bytes(12)
        aad = f"marketplace-credential:{cabinet_id}".encode()
        ciphertext = AESGCM(self._key(self.active_key_version)).encrypt(nonce, secret.encode(), aad)
        return EncryptedCredential(
            value=nonce + ciphertext,
            key_version=self.active_key_version,
            masked_hint=self.mask(secret),
        )

    def decrypt(self, value: bytes, *, key_version: int, cabinet_id: str) -> str:
        if len(value) < 29:
            raise CredentialDecryptionError("Credential payload is invalid")
        nonce, ciphertext = value[:12], value[12:]
        aad = f"marketplace-credential:{cabinet_id}".encode()
        try:
            plaintext = AESGCM(self._key(key_version)).decrypt(nonce, ciphertext, aad)
        except (InvalidTag, ValueError) as exc:
            raise CredentialDecryptionError("Credential authentication failed") from exc
        return plaintext.decode()
