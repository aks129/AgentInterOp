from typing import Optional, Dict, Any
import httpx
import asyncio


class FhirConnector:
    def __init__(self, base_url: str, token: Optional[str] = None, timeout=20.0):
        self.base = base_url.rstrip("/")
        self.headers = {"Accept": "application/fhir+json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        self.timeout = timeout

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