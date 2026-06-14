import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
from typing import Tuple


def generate_key_pair() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Generates an Ed25519 private/public key pair."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def sign_payload(private_key: ed25519.Ed25519PrivateKey, payload: str) -> str:
    """Signs a payload string and returns the base64-encoded signature."""
    signature = private_key.sign(payload.encode("utf-8"))
    return base64.b64encode(signature).decode("utf-8")


def verify_payload_signature(public_key: ed25519.Ed25519PublicKey, payload: str, signature_b64: str) -> bool:
    """Verifies a base64 signature against a payload string using the public key.

    Returns True if valid, False otherwise.
    """
    try:
        signature = base64.b64decode(signature_b64.encode("utf-8"))
        public_key.verify(signature, payload.encode("utf-8"))
        return True
    except (InvalidSignature, Exception):
        return False
