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
    entry_id = entry.entry_id
    async_add_entities([
        MateButton(coordinator, f"{entry_id}_btn_close_trip", "btn_close_trip",
                   "mdi:flag-checkered", lambda c: c.service_close_trip()),
        MateButton(coordinator, f"{entry_id}_btn_export", "btn_export",
                   "mdi:file-delimited", lambda c: None, coro=lambda c: c.service_export_csv()),
        MateButton(coordinator, f"{entry_id}_btn_reset_km", "btn_reset_km",
                   "mdi:restart", lambda c: c.service_reset_counters("km")),
        MateButton(coordinator, f"{entry_id}_btn_reset_energia", "btn_reset_energia",
                   "mdi:restart", lambda c: c.service_reset_counters("energia")),
        MateButton(coordinator, f"{entry_id}_btn_reset_costi", "btn_reset_costi",
                   "mdi:restart", lambda c: c.service_reset_counters("costi")),
    ])


class MateButton(CoordinatorEntity[RenaultMateCoordinator], ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, unique_id, key, icon,
                 sync_action=None, coro=None) -> None:
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = unique_id
        self._attr_translation_key = key
        self._attr_icon = icon
        self._sync_action = sync_action
        self._coro = coro

    async def async_press(self) -> None:
        if self._coro is not None:
            await self._coro(self.coordinator)
        elif self._sync_action is not None:
            self._sync_action(self.coordinator)
        await self.coordinator.async_request_refresh()
