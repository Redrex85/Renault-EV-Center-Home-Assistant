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
    name = str(entry.data.get("name") or entry.title or "Auto")
    wb = bool(
        entry.options.get(
            CONF_WALLBOX_ENABLED, entry.data.get(CONF_WALLBOX_ENABLED, False)
        )
    )

    entities: list[BinarySensorEntity] = [
        InCaricaSensor(coordinator, name, f"{coordinator.entry.entry_id}_in_carica",
                       f"{name} In Carica", lambda d: d["charging"]),
    ]
    if wb:
        entities.append(
            InCaricaSensor(coordinator, name, f"{coordinator.entry.entry_id}_wb_in_carica",
                           f"{name} Wallbox in Carica",
                           lambda d: d["wb_state"] in WALLBOX_CHARGING_STATES,
                           icon="mdi:ev-station"),
        )
    async_add_entities(entities)


class InCaricaSensor(CoordinatorEntity[RenaultMateCoordinator], BinarySensorEntity):
    _attr_has_entity_name = False

    def __init__(self, coordinator, name, unique_id, label, extractor,
                 device_class=BinarySensorDeviceClass.BATTERY_CHARGING, icon=None) -> None:
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = unique_id
        self._attr_name = label
        self._attr_device_class = device_class
        if icon:
            self._attr_icon = icon
        self._extractor = extractor

    @property
    def is_on(self) -> bool | None:
        return bool(self._extractor(self.coordinator.data))
