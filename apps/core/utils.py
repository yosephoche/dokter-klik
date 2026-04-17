"""Shared utility functions for DokterKlik."""


def normalize_phone(phone: str) -> str:
    """Normalize phone to digits-only E.164 format without leading +.

    Converts '0812...' → '62812...', strips spaces and dashes.
    """
    digits = ''.join(c for c in phone if c.isdigit())
    if digits.startswith('0'):
        digits = '62' + digits[1:]
    return digits
