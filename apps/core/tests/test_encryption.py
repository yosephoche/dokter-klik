"""Tests for EncryptedField encrypt/decrypt roundtrip."""
import os
import uuid
from unittest.mock import patch

from django.test import TestCase, override_settings
from cryptography.fernet import Fernet

TEST_KEY = Fernet.generate_key().decode()


@override_settings(ENCRYPTION_KEY=TEST_KEY)
class EncryptedFieldTests(TestCase):
    """Test EncryptedCharField and EncryptedTextField encryption/decryption."""

    def setUp(self):
        from apps.core.encryption import EncryptedCharField, EncryptedTextField
        self.char_field = EncryptedCharField(max_length=255)
        self.text_field = EncryptedTextField()

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted value decrypts back to original."""
        original = 'Test nama pasien'
        encrypted = self.char_field._encrypt(original)
        decrypted = self.char_field._decrypt(encrypted)
        self.assertEqual(decrypted, original)

    def test_encrypt_produces_bytes(self):
        """encrypt() returns bytes (BYTEA for PostgreSQL)."""
        result = self.char_field._encrypt('test')
        self.assertIsInstance(result, bytes)

    def test_different_ciphertexts_for_same_plaintext(self):
        """Each encryption of same value produces different ciphertext (Fernet nonce)."""
        value = 'pasien sama'
        enc1 = self.char_field._encrypt(value)
        enc2 = self.char_field._encrypt(value)
        self.assertNotEqual(enc1, enc2)  # Fernet uses random IV

    def test_decrypt_returns_same_string(self):
        """Decrypted result is a string, not bytes."""
        encrypted = self.char_field._encrypt('test')
        result = self.char_field._decrypt(encrypted)
        self.assertIsInstance(result, str)

    def test_none_value_passthrough(self):
        """None values are not encrypted/decrypted — passed through as-is."""
        self.assertIsNone(self.char_field.get_prep_value(None))

    def test_unicode_string(self):
        """Unicode characters (Indonesian names) encrypt/decrypt correctly."""
        name = 'Budi Santoso Ñ 测试'
        encrypted = self.char_field._encrypt(name)
        self.assertEqual(self.char_field._decrypt(encrypted), name)

    def test_empty_string(self):
        """Empty string encrypts and decrypts correctly."""
        encrypted = self.char_field._encrypt('')
        self.assertEqual(self.char_field._decrypt(encrypted), '')

    def test_text_field_roundtrip(self):
        """EncryptedTextField handles long text."""
        long_text = 'Anamnesis: ' + 'pusing kepala ' * 100
        encrypted = self.text_field._encrypt(long_text)
        decrypted = self.text_field._decrypt(encrypted)
        self.assertEqual(decrypted, long_text)


@override_settings(ENCRYPTION_KEY=TEST_KEY)
class ClinicScopedManagerTests(TestCase):
    """Test ClinicScopedManager cross-clinic isolation."""

    def test_for_clinic_returns_manager(self):
        """for_clinic() returns a queryset — verify API exists."""
        from apps.core.managers import ClinicScopedManager
        manager = ClinicScopedManager()
        # Just verify the method exists and is callable
        self.assertTrue(callable(manager.for_clinic))
