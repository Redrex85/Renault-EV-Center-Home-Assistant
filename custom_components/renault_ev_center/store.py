"""Persistenza su file (viaggi, ricariche, storico giornaliero, contatori)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
SAVE_DELAY = 10


class MateStore:
    """Wrapper attorno a helpers.storage.Store per un solo entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, f"renault_ev_center.{entry_id}")
        self.data: dict[str, Any] = {
            "trips": [],
            "charges": [],
            "daily": [],
            "counters": {},
            "health": {},
            "maintenance": [],
            "monthly_km": {},
            "scadenze": {},
        }

    @staticmethod
    def _valid_trip(t: Any) -> bool:
        return isinstance(t, dict) and isinstance(t.get("km"), (int, float)) and isinstance(t.get("data"), str)

    @staticmethod
    def _valid_charge(c: Any) -> bool:
        return isinstance(c, dict) and isinstance(c.get("kwh"), (int, float)) and isinstance(c.get("data"), str)

    async def async_load(self) -> None:
        try:
            raw = await self._store.async_load()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Store corrotto, riparto vuoto: %s", err)
            return
        if not raw or not isinstance(raw, dict):
            return
        trips = [t for t in raw.get("trips", []) if self._valid_trip(t)]
        charges = [c for c in raw.get("charges", []) if self._valid_charge(c)]
        if len(trips) != len(raw.get("trips", [])):
            _LOGGER.warning("Scartati %d viaggi corrotti", len(raw.get("trips", [])) - len(trips))
        if len(charges) != len(raw.get("charges", [])):
            _LOGGER.warning("Scartate %d ricariche corrotte", len(raw.get("charges", [])) - len(charges))
        self.data["trips"] = trips
        self.data["charges"] = charges
        self.data["daily"] = [d for d in raw.get("daily", []) if isinstance(d, dict)]
        self.data["health"] = raw.get("health", {}) if isinstance(raw.get("health"), dict) else {}
        self.data["maintenance"] = [m for m in raw.get("maintenance", []) if isinstance(m, dict)]
        self.data["monthly_km"] = raw.get("monthly_km", {}) if isinstance(raw.get("monthly_km"), dict) else {}
        self.data["scadenze"] = raw.get("scadenze", {}) if isinstance(raw.get("scadenze"), dict) else {}
        counters = raw.get("counters", {})
        if isinstance(counters, dict):
            self.data["counters"] = counters
        _LOGGER.debug("Store caricato: %d viaggi, %d ricariche, %d giorni",
                      len(self.data["trips"]), len(self.data["charges"]), len(self.data["daily"]))

    def save(self) -> None:
        """Salvataggio differito (debounce)."""
        payload = {
            "trips": self.data["trips"][-2000:],
            "charges": self.data["charges"][-2000:],
            "daily": self.data["daily"][-365:],
            "counters": self.data["counters"],
            "health": self.data.get("health", {}),
            "maintenance": self.data.get("maintenance", [])[-200:],
            "monthly_km": self.data.get("monthly_km", {}),
            "scadenze": self.data.get("scadenze", {}),
        }
        self._store.async_delay_save(lambda: payload, SAVE_DELAY)
