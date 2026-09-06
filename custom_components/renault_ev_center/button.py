"""Pulsanti Renault EV Center."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RenaultMateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RenaultMateCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = str(entry.data.get("name") or entry.title or "Auto")
    entry_id = entry.entry_id
    async_add_entities([
        MateButton(coordinator, name, f"{entry_id}_btn_close_trip",
                   f"{name} Chiudi Viaggio Ora", "mdi:flag-checkered",
                   lambda c: c.service_close_trip()),
        MateButton(coordinator, name, f"{entry_id}_btn_export",
                   f"{name} Esporta Viaggi CSV", "mdi:file-delimited",
                   lambda c: None, coro=lambda c: c.service_export_csv()),
        MateButton(coordinator, name, f"{entry_id}_btn_reset_km",
                   f"{name} Reset Contatori Km", "mdi:restart",
                   lambda c: c.service_reset_counters("km")),
        MateButton(coordinator, name, f"{entry_id}_btn_reset_energia",
                   f"{name} Reset Contatori Energia", "mdi:restart",
                   lambda c: c.service_reset_counters("energia")),
        MateButton(coordinator, name, f"{entry_id}_btn_reset_costi",
                   f"{name} Reset Contatori Costi", "mdi:restart",
                   lambda c: c.service_reset_counters("costi")),
    ])


class MateButton(CoordinatorEntity[RenaultMateCoordinator], ButtonEntity):
    _attr_has_entity_name = False

    def __init__(self, coordinator, name, unique_id, label, icon,
                 sync_action=None, coro=None) -> None:
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = unique_id
        self._attr_name = label
        self._attr_icon = icon
        self._sync_action = sync_action
        self._coro = coro

    async def async_press(self) -> None:
        if self._coro is not None:
            await self._coro(self.coordinator)
        elif self._sync_action is not None:
            self._sync_action(self.coordinator)
