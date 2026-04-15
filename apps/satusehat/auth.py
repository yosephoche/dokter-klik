"""OAuth 2.0 token management for SATUSEHAT API.

Tokens are cached per-clinic in Redis with TTL = expires_in - 60s buffer.
"""
import logging
import requests
import redis
from django.conf import settings

logger = logging.getLogger(__name__)


class SatusehatAuthError(Exception):
    pass


def get_satusehat_token(clinic) -> str:
    """Return a valid SATUSEHAT Bearer token for the given clinic.

    Fetches from Redis cache if available; otherwise requests a new token
    using the clinic's encrypted client credentials.
    """
    r = redis.from_url(settings.REDIS_URL)
    cache_key = f'satusehat_token_{clinic.id}'

    # Try cache first
    cached = r.get(cache_key)
    if cached:
        return cached.decode('utf-8')

    # Use a Redis lock to prevent concurrent token refresh (race condition)
    lock_key = f'satusehat_token_lock_{clinic.id}'
    with r.lock(lock_key, timeout=30):
        # Double-check after acquiring lock
        cached = r.get(cache_key)
        if cached:
            return cached.decode('utf-8')

        client_id = clinic.satusehat_client_id  # auto-decrypted by EncryptedCharField
        client_secret = clinic.satusehat_client_secret

        if not client_id or not client_secret:
            raise SatusehatAuthError(
                f'SATUSEHAT credentials not configured for clinic {clinic.name}'
            )

        token_url = f'{settings.SATUSEHAT_BASE_URL}/oauth2/v1/accesstoken'
        try:
            resp = requests.post(
                token_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise SatusehatAuthError(f'Failed to fetch SATUSEHAT token: {exc}') from exc

        token = data.get('access_token')
        expires_in = int(data.get('expires_in', 300))
        ttl = max(expires_in - 60, 60)  # 60s buffer; minimum 60s TTL

        r.setex(cache_key, ttl, token)
        logger.info('SATUSEHAT token refreshed for clinic %s (TTL=%ds)', clinic.name, ttl)
        return token
