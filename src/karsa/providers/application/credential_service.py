"""Credential encryption service — AES-256-GCM.

Sprint-51: Encrypts API keys at rest. Master key injected via
DATA_BRIDGE_MASTER_KEY environment variable.
"""
import os
import base64
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from karsa.providers.domain.data_bridge import EncryptedCredential


class MissingMasterKeyError(Exception):
    """Raised when DATA_BRIDGE_MASTER_KEY is not set."""


class CredentialDecryptionError(Exception):
    """Raised when decryption fails (wrong key, corrupted data)."""


class CredentialEncryptionService:
    """AES-256-GCM encrypt/decrypt for provider API keys.

    The master key must be a 32-byte key encoded as base64,
    injected via the DATA_BRIDGE_MASTER_KEY environment variable.
    """

    def __init__(self, master_key_b64: Optional[str] = None):
        key_b64 = master_key_b64 or os.environ.get("DATA_BRIDGE_MASTER_KEY")
        if not key_b64:
            raise MissingMasterKeyError(
                "DATA_BRIDGE_MASTER_KEY environment variable is not set. "
                "Cannot encrypt/decrypt provider credentials."
            )
        try:
            self._key = base64.b64decode(key_b64)
            if len(self._key) != 32:
                raise ValueError("Key must be 32 bytes for AES-256")
        except Exception as e:
            raise MissingMasterKeyError(
                f"DATA_BRIDGE_MASTER_KEY is invalid: {e}"
            )
        self._aesgcm = AESGCM(self._key)

    def encrypt(
        self,
        plaintext: str,
        key_rotation_version: int = 1,
    ) -> EncryptedCredential:
        """Encrypt a plaintext credential."""
        import os as _os
        nonce = _os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return EncryptedCredential(
            ciphertext=base64.b64encode(ciphertext).decode("ascii"),
            nonce=base64.b64encode(nonce).decode("ascii"),
            key_rotation_version=key_rotation_version,
        )

    def decrypt(self, credential: EncryptedCredential) -> str:
        """Decrypt an encrypted credential back to plaintext."""
        try:
            ciphertext = base64.b64decode(credential.ciphertext)
            nonce = base64.b64decode(credential.nonce)
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception as e:
            raise CredentialDecryptionError(
                f"Failed to decrypt credential (rotation v{credential.key_rotation_version}): {e}"
            )
