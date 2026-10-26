"""
AES-256-GCM At-Rest Encryption for Brigade.
Provides authenticated encryption for sensitive payloads, credentials,
memory records, and transcripts.
"""
import os
import secrets
from pathlib import Path
from typing import Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from brigade_core import get_state_dir


class EncryptionManager:
    """Handles at-rest encryption keys and AES-256-GCM operations."""

    def __init__(self, key_path: Optional[Path] = None):
        self.state_dir = get_state_dir()
        self.key_path = key_path or (self.state_dir / "encryption.key")

    def get_key(self) -> Optional[bytes]:
        """Resolves the 32-byte master key from environment or keyfile."""
        env_key = os.environ.get("BRIGADE_ENCRYPTION_KEY")
        if env_key:
            try:
                raw = bytes.fromhex(env_key.strip())
                if len(raw) == 32:
                    return raw
            except Exception:
                pass

        if self.key_path.exists():
            try:
                hex_str = self.key_path.read_text(encoding="utf-8").strip()
                raw = bytes.fromhex(hex_str)
                if len(raw) == 32:
                    return raw
            except Exception:
                pass
        return None

    def init_key(self) -> str:
        """Generates a new 32-byte cryptographically secure key and stores it."""
        key = secrets.token_bytes(32)
        hex_key = key.hex()
        self.key_path.write_text(hex_key, encoding="utf-8")
        try:
            os.chmod(self.key_path, 0o600)
        except Exception:
            pass
        return hex_key

    def is_enabled(self) -> bool:
        """Checks if a valid key is configured."""
        return self.get_key() is not None

    def encrypt(self, plaintext: str, associated_data: Optional[bytes] = None) -> str:
        """Encrypts plaintext with AES-256-GCM and returns hex-encoded (nonce + ciphertext + tag)."""
        key = self.get_key()
        if not key:
            raise RuntimeError("Encryption key not configured. Run 'brigade encrypt init' first.")

        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)  # 96-bit nonce
        data_bytes = plaintext.encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, data_bytes, associated_data)
        payload = nonce + ciphertext
        return payload.hex()

    def decrypt(self, hex_payload: str, associated_data: Optional[bytes] = None) -> str:
        """Decrypts hex-encoded payload containing nonce and ciphertext."""
        key = self.get_key()
        if not key:
            raise RuntimeError("Encryption key not configured.")

        payload = bytes.fromhex(hex_payload)
        if len(payload) < 28:
            raise ValueError("Invalid encrypted payload length.")

        nonce = payload[:12]
        ciphertext = payload[12:]
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, ciphertext, associated_data)
        return decrypted.decode("utf-8")

    def test_roundtrip(self) -> bool:
        """Verifies encrypt/decrypt round-trip on a probe string."""
        sample = "brigade_encryption_test_payload_123456"
        enc = self.encrypt(sample)
        dec = self.decrypt(enc)
        return dec == sample
