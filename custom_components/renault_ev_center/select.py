"""Select Renault EV Center: filtri per la lista ricariche."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RenaultMateCoordinator

_LOGGER = logging.getLogger(__name__)

TIPI = ["Tutte", "Casa", "Fotovoltaico", "Pubblica"]
PERIODI = ["Settimana", "Mese", "Anno", "Tutto"]
ANNI = ["Tutti"] + [str(a) for a in range(2024, 2033)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RenaultMateCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = str(entry.data.get("name") or entry.title or "Renault")
    async_add_entities([
        MateSelect(coordinator, f"{name} Filtro Tipo Ricarica", "filtro_tipo", TIPI, "Tutte", "mdi:filter-variant"),
        MateSelect(coordinator, f"{name} Filtro Periodo Ricariche", "filtro_periodo", PERIODI, "Mese", "mdi:calendar-range"),
        MateSelect(coordinator, f"{name} Filtro Anno Ricariche", "filtro_anno", ANNI, "Tutti", "mdi:calendar-multiple"),
    ])


class MateSelect(CoordinatorEntity[RenaultMateCoordinator], RestoreEntity, SelectEntity):
    _attr_has_entity_name = False

    def __init__(self, coordinator, label, key, options, default, icon) -> None:
        super().__init__(coordinator)
        self._key = key
        self._options = options
        self._default = default
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.entry.entry_id}_sel_{key}"
        self._attr_name = label
        self._attr_icon = icon
        self._attr_options = options
        self._attr_current_option = default

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in self._options:
            self._attr_current_option = last.state
        self.coordinator.register_setting("select", self._key, self.entity_id)

    async def async_select_option(self, option: str) -> None:
        if option in self._options:
            self._attr_current_option = option
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
