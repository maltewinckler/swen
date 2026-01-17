"""Unit tests for FernetEncryptionService."""

import pytest
from cryptography.fernet import Fernet

from swen.domain.security.exceptions import DecryptionError
from swen.infrastructure.security import FernetEncryptionService


class TestFernetEncryptionService:
    """Test Fernet encryption service."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt/decrypt work correctly."""
        key = Fernet.generate_key()
        service = FernetEncryptionService(key)

        plaintext = "my_secret_password_123"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext
        assert encrypted != plaintext.encode()  # Must be encrypted
        assert isinstance(encrypted, bytes)

    def test_encrypted_data_is_different_each_time(self):
        """Test that same plaintext produces different ciphertexts (IV)."""
        key = Fernet.generate_key()
        service = FernetEncryptionService(key)

        plaintext = "same_text"
        encrypted1 = service.encrypt(plaintext)
        encrypted2 = service.encrypt(plaintext)

        # Different ciphertexts (due to random IV)
        assert encrypted1 != encrypted2

        # But both decrypt to same plaintext
        assert service.decrypt(encrypted1) == plaintext
        assert service.decrypt(encrypted2) == plaintext

    def test_different_keys_cannot_decrypt(self):
        """Test that wrong key cannot decrypt data."""
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()

        service1 = FernetEncryptionService(key1)
        service2 = FernetEncryptionService(key2)

        plaintext = "secret"
        encrypted = service1.encrypt(plaintext)

        # Wrong key should fail
        with pytest.raises(DecryptionError, match="Invalid token"):
            service2.decrypt(encrypted)

    def test_tampered_data_raises_error(self):
        """Test that tampered ciphertext raises error (HMAC protection)."""
        key = Fernet.generate_key()
        service = FernetEncryptionService(key)

        plaintext = "secret"
        encrypted = service.encrypt(plaintext)

        # Tamper with the data
        tampered = encrypted[:-1] + b"X"

        with pytest.raises(DecryptionError, match="Invalid token"):
            service.decrypt(tampered)

    def test_invalid_key_raises_error(self):
        """Test that invalid key raises error on init."""
        with pytest.raises(ValueError, match="Invalid Fernet"):
            FernetEncryptionService(b"not-a-valid-key")

    def test_generate_key_returns_valid_key(self):
        """Test static key generation method."""
        key = FernetEncryptionService.generate_key()

        # Should be valid Fernet key
        service = FernetEncryptionService(key)
        plaintext = "test"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        key = Fernet.generate_key()
        service = FernetEncryptionService(key)

        plaintext = ""
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == ""

    def test_encrypt_unicode(self):
        """Test encrypting unicode characters."""
        key = Fernet.generate_key()
        service = FernetEncryptionService(key)

        plaintext = "Passwörd_with_émoji_"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext
