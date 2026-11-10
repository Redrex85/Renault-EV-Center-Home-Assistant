"""Binary sensor Renault EV Center."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_WALLBOX_ENABLED, WALLBOX_CHARGING_STATES, DOMAIN
from .coordinator import RenaultMateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RenaultMateCoordinator = hass.data[DOMAIN][entry.entry_id]
    wb = bool(
        entry.options.get(
            CONF_WALLBOX_ENABLED, entry.data.get(CONF_WALLBOX_ENABLED, False)
        )
    )

    entities: list[BinarySensorEntity] = [
        InCaricaSensor(coordinator, f"{coordinator.entry.entry_id}_in_carica",
                       "in_carica", lambda d: d["charging"]),
    ]
    if wb:
        entities.append(
            InCaricaSensor(coordinator, f"{coordinator.entry.entry_id}_wb_in_carica",
                           "wb_in_carica",
                           lambda d: d["wb_state"] in WALLBOX_CHARGING_STATES,
                           icon="mdi:ev-station"),
        )
    async_add_entities(entities)


class InCaricaSensor(CoordinatorEntity[RenaultMateCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, unique_id, key, extractor,
                 device_class=BinarySensorDeviceClass.BATTERY_CHARGING, icon=None) -> None:
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = unique_id
        self._attr_translation_key = key
        self._attr_device_class = device_class
        if icon:
            self._attr_icon = icon
        self._extractor = extractor

    @property
    def is_on(self) -> bool | None:
        return bool(self._extractor(self.coordinator.data))
