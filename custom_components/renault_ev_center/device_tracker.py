"""Device tracker Renault EV Center: posizione dell'auto dall'integrazione Renault."""
from __future__ import annotations

import logging

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_LOCATION_ENTITY, DOMAIN
from .coordinator import RenaultMateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RenaultMateCoordinator = hass.data[DOMAIN][entry.entry_id]
    opts = {**entry.data, **entry.options}
    source = opts.get(CONF_LOCATION_ENTITY)
    if not source or hass.states.get(str(source)) is None:
        _LOGGER.info("Nessun tracker GPS configurato: device_tracker non creato")
        return
    name = str(entry.data.get("name") or entry.title or "Renault")
    async_add_entities([MateDeviceTracker(coordinator, name, str(source))])


class MateDeviceTracker(CoordinatorEntity[RenaultMateCoordinator], TrackerEntity):
    """Specchia il device_tracker Renault come entità dell'integrazione."""

    _attr_has_entity_name = False
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: RenaultMateCoordinator, name: str, source: str) -> None:
        super().__init__(coordinator)
        self._source = source
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.entry.entry_id}_tracker"
        self._attr_name = f"{name} Posizione"
        self._attr_icon = "mdi:car-connected"

    @property
    def _src(self):
        return self.hass.states.get(self._source)

    @property
    def latitude(self) -> float | None:
        s = self._src
        return s.attributes.get("latitude") if s else None

    @property
    def longitude(self) -> float | None:
        s = self._src
        return s.attributes.get("longitude") if s else None

    @property
    def location_accuracy(self) -> int:
        s = self._src
        try:
            return int(s.attributes.get("gps_accuracy") or 0)
        except (TypeError, ValueError):
            return 0
