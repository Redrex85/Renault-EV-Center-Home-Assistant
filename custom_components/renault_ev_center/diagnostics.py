"""Diagnostica (redatta) per Renault EV Center.

Espone solo stato e motivi — nessun valore sensibile, nessun host/IP: serve a capire
PERCHÉ una fonte non risponde (cloud Renault non raggiungibile, entità unavailable,
geocoding fallito) da un report.
"""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Snapshot redatto dello stato dell'integrazione."""
    coord = (hass.data.get(DOMAIN) or {}).get(entry.entry_id)
    if coord is None:
        return {"error": "coordinator non disponibile"}
    iv = coord.update_interval
    store = coord.store.data
    return {
        "version": coord.version,
        "last_update_success": bool(coord.last_update_success),
        "last_success": coord.last_success,
        "last_error": coord.last_error,
        "update_interval_s": int(iv.total_seconds()) if iv else None,
        "geocode": dict(coord.geocode_stats),
        "source_entities": coord.source_status(),
        "store": {
            "trips": len(store.get("trips", [])),
            "charges": len(store.get("charges", [])),
            "daily": len(store.get("daily", [])),
            "maintenance": len(store.get("maintenance", [])),
        },
    }
