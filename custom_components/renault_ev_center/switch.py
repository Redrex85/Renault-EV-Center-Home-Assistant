"""Switch Renault EV Center: abilita notifiche e automazioni di ricarica."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
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
    name = str(entry.data.get("name") or entry.title or "Renault")
    async_add_entities([
        MateSwitch(coordinator, "notify_start", f"{name} Notifica Avvio Ricarica",
                   True, "mdi:battery-charging"),
        MateSwitch(coordinator, "notify_end", f"{name} Notifica Fine Ricarica",
                   True, "mdi:battery-charging-complete"),
        MateSwitch(coordinator, "low_soc", f"{name} Promemoria Batteria Bassa",
                   True, "mdi:battery-alert"),
        MateSwitch(coordinator, "charge_sched", f"{name} Carica Programmata",
                   False, "mdi:calendar-clock"),
        MateSwitch(coordinator, "balance", f"{name} Bilanciamento Solare",
                   False, "mdi:solar-power"),
    ])


class MateSwitch(CoordinatorEntity[RenaultMateCoordinator], RestoreEntity, SwitchEntity):
    _attr_has_entity_name = False

    def __init__(self, coordinator, key, label, default, icon) -> None:
        super().__init__(coordinator)
        self._key = key
        self._default = default
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.entry.entry_id}_sw_{key}"
        self._attr_name = label
        self._attr_icon = icon
        self._attr_is_on = default

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in ("on", "off"):
            self._attr_is_on = last.state == "on"
        self.coordinator.register_setting("switch", self._key, self.entity_id)

    @property
    def is_on(self) -> bool:
        return bool(self._attr_is_on)

    async def async_turn_on(self, **kwargs) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
