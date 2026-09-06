"""Number Renault EV Center: prezzi, capacità, obiettivo e SOH modificabili da dashboard."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CAPACITY,
    CONF_PRICE_HOME,
    CONF_PRICE_PUBLIC,
    CONF_PRICE_SOLAR,
    CONF_TARGET_SOC,
    DOMAIN,
)
from .coordinator import RenaultMateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RenaultMateCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = str(entry.data.get("name") or entry.title or "Renault")
    base = {**entry.data, **entry.options}

    defs = [
        ("price_home", f"{name} Costo Energia Casa",
         float(base.get(CONF_PRICE_HOME, 0.25)), 0.0, 5.0, 0.001, "€/kWh", "mdi:home-lightning-bolt"),
        ("price_public", f"{name} Costo Colonnina",
         float(base.get(CONF_PRICE_PUBLIC, 0.45)), 0.0, 5.0, 0.001, "€/kWh", "mdi:ev-station"),
        ("price_solar", f"{name} Costo Fotovoltaico",
         float(base.get(CONF_PRICE_SOLAR, 0.0)), 0.0, 5.0, 0.001, "€/kWh", "mdi:solar-power"),
        ("capacity", f"{name} Capacita Batteria",
         float(base.get(CONF_CAPACITY, 60.0)), 20.0, 150.0, 0.5, "kWh", "mdi:car-battery"),
        ("target", f"{name} Obiettivo Ricarica",
         float(base.get(CONF_TARGET_SOC, 80.0)), 50.0, 100.0, 1.0, "%", "mdi:battery-charging-100"),
        ("soh_official", f"{name} SOH Ufficiale",
         100.0, 50.0, 100.0, 0.1, "%", "mdi:heart-pulse"),
        ("assic_costo", f"{name} Costo Assicurazione",
         float(base.get("assicurazione_costo", 400.0)), 0.0, 3000.0, 10.0, "€/anno", "mdi:shield-car"),
        ("low_soc", f"{name} Batteria Minima Promemoria",
         float(base.get("low_soc_threshold", 25.0)), 5.0, 80.0, 1.0, "%", "mdi:battery-alert"),
        ("charge_start_soc", f"{name} Carica Avvio Sotto",
         float(base.get("charge_start_soc", 30.0)), 5.0, 80.0, 1.0, "%", "mdi:play-circle"),
        ("charge_stop_soc", f"{name} Carica Ferma Sopra",
         float(base.get("charge_stop_soc", 80.0)), 50.0, 100.0, 1.0, "%", "mdi:stop-circle"),
        ("balance_min_amps", f"{name} Bilanciamento Ampere Minimi",
         6.0, 4.0, 32.0, 1.0, "A", "mdi:current-ac"),
        ("balance_max_amps", f"{name} Bilanciamento Ampere Massimi",
         float(base.get("balance_max_amps", 16.0)), 6.0, 32.0, 1.0, "A", "mdi:current-ac"),
        ("battery_priority", f"{name} Priorità Batteria Casa",
         float(base.get("battery_priority_min", 80.0)), 0.0, 100.0, 5.0, "%", "mdi:home-battery"),
    ]
    async_add_entities([
        MateNumber(coordinator, key, label, initial, vmin, vmax, step, unit, icon)
        for key, label, initial, vmin, vmax, step, unit, icon in defs
    ])


class MateNumber(CoordinatorEntity[RenaultMateCoordinator], RestoreEntity, NumberEntity):
    _attr_has_entity_name = False
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, key, label, initial, vmin, vmax, step, unit, icon) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.entry.entry_id}_num_{key}"
        self._attr_name = label
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_native_min_value = vmin
        self._attr_native_max_value = vmax
        self._attr_native_step = step
        self._initial = initial

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            try:
                self._attr_native_value = float(last.state)
            except (TypeError, ValueError):
                self._attr_native_value = self._initial
        else:
            self._attr_native_value = self._initial
        self.coordinator.register_setting("number", self._key, self.entity_id)

    @property
    def native_value(self):
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = round(value, 3)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
