"""Senden an die Cloud Function ingest (gleiche Schnittstelle wie pi-dienst/cloud.py)."""
from __future__ import annotations

import logging

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import INGEST_URL

_LOGGER = logging.getLogger(__name__)
MAX_PER_REQUEST = 250


async def post(hass: HomeAssistant, key: str, body: dict) -> int:
    """HTTP-Status der Antwort; 0 bei Netzfehler. 401 = Schlüssel unbekannt, 402 = kein Plan Live."""
    try:
        async with async_get_clientsession(hass).post(
            INGEST_URL, json=body, headers={"Authorization": f"Bearer {key.strip()}"}, timeout=aiohttp.ClientTimeout(total=20)
        ) as res:
            if res.status >= 400 and res.status not in (401, 402):
                _LOGGER.warning("myEnergy antwortet %s: %s", res.status, (await res.text())[:200])
            return res.status
    except (aiohttp.ClientError, TimeoutError) as err:
        _LOGGER.debug("myEnergy nicht erreichbar: %s", err)
        return 0


async def send(hass: HomeAssistant, key: str, writes: list[dict]) -> int:
    """Schreibaufträge in Paketen senden; der erste Fehler bricht ab und wird zurückgegeben."""
    for i in range(0, len(writes), MAX_PER_REQUEST):
        status = await post(hass, key, {"writes": writes[i : i + MAX_PER_REQUEST]})
        if status != 200:
            return status
    return 200
