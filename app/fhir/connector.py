from typing import Optional, Dict, Any
import httpx
import asyncio
from urllib.parse import urlparse
import ipaddress

# Security: Allowed FHIR server hosts (prevent SSRF)
ALLOWED_FHIR_HOSTS = {
    "hapi.fhir.org",
    "r4.smarthealthit.org",
    "launch.smarthealthit.org",
    "fhirtest.uhn.ca",
    "server.fire.ly"
}

def validate_fhir_url(url: str) -> bool:
    """Validate FHIR URL to prevent SSRF attacks"""
    try:
        parsed = urlparse(url)
        
        # Must be HTTPS
        if parsed.scheme != "https":
            return False
        
        # Check if host is in allowlist
        if parsed.hostname in ALLOWED_FHIR_HOSTS:
            return True
            
        # Block private/internal IP ranges
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            return not ip.is_private and not ip.is_loopback and not ip.is_reserved
        except ValueError:
            # Hostname is not an IP, check if it's allowed
            return False
    except Exception:
        return False


class FhirConnector:
    def __init__(self, base_url: str, token: Optional[str] = None, timeout=20.0):
        # Security validation
        if not validate_fhir_url(base_url):
            raise ValueError(f"Invalid or unauthorized FHIR URL: {base_url}")
            
        self.base = base_url.rstrip("/")
        self.headers = {"Accept": "application/fhir+json"}
        if token:
            # Basic token validation - must be non-empty and reasonable length
            if not token.strip() or len(token) < 8 or len(token) > 2048:
                raise ValueError("Invalid FHIR token format")
            self.headers["Authorization"] = f"Bearer {token}"
        self.timeout = min(timeout, 30.0)  # Cap timeout

    async def get_json(self, path: str, params: Dict[str, Any] | None = None):
        url = f"{self.base}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(url, headers=self.headers, params=params)
            r.raise_for_status()
            return r.json()

    async def capabilities(self):
        return await self.get_json("metadata")

    async def patient_everything(self, patient_id: str):
        return await self.get_json(f"Patient/{patient_id}/$everything")

    async def search(self, resource: str, **params):
        return await self.get_json(resource, params=params)