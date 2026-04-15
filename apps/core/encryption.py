"""Fernet-based transparent field encryption for sensitive PII/medical data.

IMPORTANT: EncryptedField stores data as BYTEA. ORM filter (e.g. icontains)
WILL NOT WORK on encrypted fields because each encryption produces different
ciphertext. Use a companion plaintext search field (e.g. name_search) for
filtering. See Patient.name_search for the pattern.
"""
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        raise ValueError(
            'ENCRYPTION_KEY is not set. Generate with: '
            'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


class EncryptedMixin:
    """Mixin providing encrypt/decrypt helpers."""

    def _encrypt(self, value: str) -> bytes:
        if not isinstance(value, str):
            value = str(value)
        return _get_fernet().encrypt(value.encode('utf-8'))

    def _decrypt(self, value: bytes) -> str:
        try:
            return _get_fernet().decrypt(bytes(value)).decode('utf-8')
        except (InvalidToken, Exception):
            return ''


class EncryptedCharField(EncryptedMixin, models.BinaryField):
    """Encrypts char data at-rest using Fernet. Stored as BYTEA."""

    def __init__(self, *args, max_length=None, **kwargs):
        # BinaryField ignores max_length but we keep it for API consistency
        kwargs.pop('max_length', None)
        super().__init__(*args, **kwargs)
        self.max_length = max_length  # informational only

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.max_length is not None:
            kwargs['max_length'] = self.max_length
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self._decrypt(bytes(value))

    def get_prep_value(self, value):
        if value is None:
            return value
        if isinstance(value, memoryview):
            return value  # already encrypted bytes
        return self._encrypt(str(value))

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, (bytes, memoryview)):
            return self._decrypt(bytes(value))
        return value


class EncryptedTextField(EncryptedMixin, models.BinaryField):
    """Encrypts long text data at-rest using Fernet. Stored as BYTEA."""

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self._decrypt(bytes(value))

    def get_prep_value(self, value):
        if value is None:
            return value
        if isinstance(value, memoryview):
            return value
        return self._encrypt(str(value))

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, (bytes, memoryview)):
            return self._decrypt(bytes(value))
        return value
