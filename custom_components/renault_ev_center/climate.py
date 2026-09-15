"""Climate Renault EV Center: pre-climatizzazione abitacolo (wrap del climate Renault)."""
from __future__ import annotations

import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RenaultMateCoordinator
from .dashboard import slugify

_LOGGER = logging.getLogger(__name__)


def _find_climate(hass: HomeAssistant, coordinator: RenaultMateCoordinator, name: str) -> str | None:
    opts = coordinator.opts
    for cand in (opts.get("climate_entity"), f"climate.{slugify(name)}"):
        if cand and hass.states.get(str(cand)):
            return str(cand)
    lname = str(name).lower()
    for state in hass.states.async_all("climate"):
        friendly = str(state.attributes.get("friendly_name", "")).lower()
        if lname in friendly or "renault" in friendly:
            return state.entity_id
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RenaultMateCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = str(entry.data.get("name") or entry.title or "Renault")
    source = _find_climate(hass, coordinator, name)
    if not source:
        _LOGGER.info("Nessuna entità climate Renault trovata: climate non creato")
        return
    async_add_entities([MateClimate(coordinator, name, source)])


class MateClimate(CoordinatorEntity[RenaultMateCoordinator], ClimateEntity):
    """Pre-climatizzazione: inoltra i comandi al climate dell'integrazione Renault."""

    _attr_has_entity_name = False
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT_COOL]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 15
    _attr_max_temp = 25
    _attr_target_temperature_step = 1

    def __init__(self, coordinator: RenaultMateCoordinator, name: str, source: str) -> None:
        super().__init__(coordinator)
        self._source = source
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.entry.entry_id}_climate"
        self._attr_name = f"{name} Climatizzatore"

    @property
    def _src(self):
        return self.hass.states.get(self._source)

    @property
    def hvac_mode(self) -> HVACMode | None:
        s = self._src
        if s is None:
            return None
        return HVACMode.OFF if s.state in ("off", "unavailable", "unknown") else HVACMode.HEAT_COOL

    @property
    def target_temperature(self) -> float | None:
        s = self._src
        return s.attributes.get("temperature") if s else None

    @property
    def current_temperature(self) -> float | None:
        s = self._src
        return s.attributes.get("current_temperature") if s else None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        service = "turn_off" if hvac_mode == HVACMode.OFF else "turn_on"
        await self.hass.services.async_call(
            "climate", service, {"entity_id": self._source}, blocking=True
        )

    async def async_set_temperature(self, **kwargs) -> None:
        temp = kwargs.get("temperature")
        if temp is None:
            return
        await self.hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": self._source, "temperature": temp},
            blocking=True,
        )
