"""Time Renault EV Center: orari di promemoria e carica programmata regolabili da dashboard."""
from __future__ import annotations

import logging
from datetime import time as dt_time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RenaultMateCoordinator

_LOGGER = logging.getLogger(__name__)


def _parse(hhmm: str) -> dt_time:
    try:
        parts = str(hhmm).split(":")
        return dt_time(int(parts[0]), int(parts[1]))
    except (ValueError, TypeError, IndexError):
        return dt_time(0, 0)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RenaultMateCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = str(entry.data.get("name") or entry.title or "Renault")
    base = {**entry.data, **entry.options}

    defs = [
        ("low_soc_start", f"{name} Promemoria Inizio", base.get("low_soc_start", "18:00"), "mdi:clock-start"),
        ("low_soc_end", f"{name} Promemoria Fine", base.get("low_soc_end", "22:00"), "mdi:clock-end"),
        ("charge_start_time", f"{name} Carica Orario Avvio", base.get("charge_start_time", "23:30"), "mdi:play-circle"),
        ("charge_stop_time", f"{name} Carica Orario Stop", base.get("charge_stop_time", "07:00"), "mdi:stop-circle"),
    ]
    async_add_entities([
        MateTime(coordinator, key, label, _parse(initial), icon)
        for key, label, initial, icon in defs
    ])


class MateTime(CoordinatorEntity[RenaultMateCoordinator], RestoreEntity, TimeEntity):
    _attr_has_entity_name = False

    def __init__(self, coordinator, key, label, initial: dt_time, icon) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.entry.entry_id}_time_{key}"
        self._attr_name = label
        self._attr_icon = icon
        self._attr_native_value = initial

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state not in ("unknown", "unavailable", None):
            try:
                hh, mm = last.state.split(":")[0], last.state.split(":")[1]
                self._attr_native_value = dt_time(int(hh), int(mm))
            except (ValueError, TypeError, IndexError):
                pass
        self.coordinator.register_setting("time", self._key, self.entity_id)

    @property
    def native_value(self) -> dt_time | None:
        return self._attr_native_value

    async def async_set_value(self, value: dt_time) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
