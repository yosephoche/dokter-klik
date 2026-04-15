"""HTTP client for SATUSEHAT FHIR R4 API."""
import logging
import requests
from django.conf import settings
from .auth import get_satusehat_token, SatusehatAuthError

logger = logging.getLogger(__name__)


class SatusehatAPIError(Exception):
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class SatusehatClient:
    """Authenticated FHIR R4 client for SATUSEHAT."""

    def __init__(self, clinic):
        self.clinic = clinic
        self.base_url = settings.SATUSEHAT_BASE_URL

    def _get_headers(self) -> dict:
        token = get_satusehat_token(self.clinic)
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

    def post_resource(self, resource_type: str, payload: dict) -> dict:
        """POST a FHIR resource to SATUSEHAT. Returns parsed response dict."""
        url = f'{self.base_url}/fhir-r4/v1/{resource_type}'
        try:
            resp = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30,
            )
            if resp.status_code == 401:
                # Token may have expired; invalidate cache and retry once
                import redis
                r = redis.from_url(settings.REDIS_URL)
                r.delete(f'satusehat_token_{self.clinic.id}')
                resp = requests.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30,
                )
            resp.raise_for_status()
            return resp.json()
        except requests.Timeout as exc:
            raise SatusehatAPIError(
                f'SATUSEHAT API timeout for {resource_type}', status_code=408
            ) from exc
        except requests.HTTPError as exc:
            raise SatusehatAPIError(
                f'SATUSEHAT API error for {resource_type}: {exc}',
                status_code=exc.response.status_code,
                response=exc.response,
            ) from exc

    def put_resource(self, resource_type: str, resource_id: str, payload: dict) -> dict:
        """PUT to update an existing FHIR resource."""
        url = f'{self.base_url}/fhir-r4/v1/{resource_type}/{resource_id}'
        try:
            resp = requests.put(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            raise SatusehatAPIError(f'SATUSEHAT PUT error: {exc}') from exc
