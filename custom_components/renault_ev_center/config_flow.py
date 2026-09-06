"""Config flow Renault EV Center: selezione guidata delle entità."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
)

from .const import (
    CONF_BATTERY_LEVEL,
    CONF_BOLLO_EV,
    CONF_BOLLO_TERMICO,
    CONF_CAPACITY,
    CONF_CHARGING_EFFICIENCY,
    CONF_CHARGING_ENTITY,
    CONF_CHARGE_SCHED_ENABLED,
    CONF_CHARGE_SCHED_MODE,
    CONF_CHARGE_START_TIME,
    CONF_CHARGE_STOP_TIME,
    CONF_CHARGE_START_SOC,
    CONF_CHARGE_STOP_SOC,
    CONF_CHARGE_START_BUTTON,
    CONF_CHARGE_TARGET_NUMBER,
    CONF_CREATE_DASHBOARD,
    CONF_WB_CHARGE_SWITCH,
    CONF_HAS_PV,
    CONF_BALANCE_GRID_SENSOR,
    CONF_BALANCE_BATTERY_SENSOR,
    CONF_BALANCE_INVERT_GRID,
    CONF_BALANCE_INCLUDE_BATTERY,
    CONF_BALANCE_WPA,
    CONF_BALANCE_BATTERY_SOC_SENSOR,
    CONF_BATTERY_PRIORITY_MIN,
    CONF_LOW_SOC_ENABLED,
    CONF_LOW_SOC_THRESHOLD,
    CONF_LOW_SOC_START,
    CONF_LOW_SOC_END,
    CONF_MODEL,
    MODELS,
    CONF_CO2_ENABLED,
    CONF_CO2_GRID_GKWH,
    CONF_CO2_THERMAL_GKM,
    CONF_DIESEL_PRICE_ENTITY,
    CONF_FUEL_CONSUMPTION,
    CONF_FUEL_ENABLED,
    CONF_FUEL_LABEL,
    CONF_FUEL_PRICE,
    CONF_LOCATION_ENTITY,
    CONF_MAINT_ENABLED,
    CONF_ASSICURAZIONE_COSTO,
    CONF_ASSICURAZIONE_DATA,
    CONF_NOTIFY_CHARGE_END,
    CONF_NOTIFY_CHARGE_START,
    CONF_NOTIFY_DAYS,
    CONF_NOTIFY_SERVICE,
    CONF_TAGLIANDO_DATA,
    CONF_TAGLIANDO_MODE,
    CONF_NAME,
    CONF_ODOMETER,
    CONF_PLUG_ENTITY,
    CONF_POLL_INTERVAL,
    CONF_PRICE_HOME,
    CONF_PRICE_PUBLIC,
    CONF_PRICE_SOLAR,
    CONF_RANGE,
    CONF_SCAD_ASSICURAZIONE,
    CONF_SCAD_BOLLO,
    CONF_SCAD_REVISIONE,
    CONF_SCADENZE_ENABLED,
    CONF_SOLAR_ZONE,
    CONF_TAG_EV,
    CONF_TAG_TERMICO,
    CONF_TAGLIANDO_INTERVALLO,
    CONF_TARGET_SOC,
    CONF_TEMP_ENTITY,
    CONF_TRIP_TIMEOUT,
    CONF_WALLBOX_ENABLED,
    CONF_WB_MAX_CURRENT,
    CONF_WB_POWER,
    CONF_WB_SESSION_ENERGY,
    CONF_WB_STATE,
    CONF_WB_TOTAL_ENERGY,
    DEFAULT_BOLLO_EV,
    DEFAULT_BOLLO_TERMICO,
    DEFAULT_CAPACITY,
    DEFAULT_CO2_GRID_GKWH,
    DEFAULT_CO2_THERMAL_GKM,
    DEFAULT_EFFICIENCY,
    DEFAULT_FUEL_CONSUMPTION,
    DEFAULT_FUEL_LABEL,
    DEFAULT_FUEL_PRICE,
    DEFAULT_NAME,
    DEFAULT_LOW_SOC_THRESHOLD,
    DEFAULT_MAX_AMPS,
    DEFAULT_MIN_AMPS,
    DEFAULT_BATTERY_PRIORITY,
    DEFAULT_WPA,
    DEFAULT_LOW_SOC_START,
    DEFAULT_LOW_SOC_END,
    DEFAULT_NOTIFY_DAYS,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PRICE_HOME,
    DEFAULT_PRICE_PUBLIC,
    DEFAULT_PRICE_SOLAR,
    DEFAULT_SOLAR_ZONE,
    DEFAULT_TAG_EV,
    DEFAULT_TAG_TERMICO,
    DEFAULT_TAGLIANDO_INTERVALLO,
    DEFAULT_ASSICURAZIONE_COSTO,
    DEFAULT_TARGET_SOC,
    DEFAULT_TRIP_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PERCENT_SENSOR = EntitySelectorConfig(domain="sensor")
ENERGY_SENSOR = EntitySelectorConfig(domain="sensor")


def _car_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
        vol.Required(
            CONF_ODOMETER, description={"suggested_value": defaults.get(CONF_ODOMETER)}
        ): EntitySelector(EntitySelectorConfig(domain="sensor")),
        vol.Required(
            CONF_BATTERY_LEVEL, description={"suggested_value": defaults.get(CONF_BATTERY_LEVEL)}
        ): EntitySelector(PERCENT_SENSOR),
        vol.Required(
            CONF_RANGE, description={"suggested_value": defaults.get(CONF_RANGE)}
        ): EntitySelector(EntitySelectorConfig(domain="sensor")),
        vol.Required(
            CONF_CHARGING_ENTITY, description={"suggested_value": defaults.get(CONF_CHARGING_ENTITY)}
        ): EntitySelector(EntitySelectorConfig(domain=["binary_sensor", "sensor"])),
        vol.Optional(
            CONF_PLUG_ENTITY, description={"suggested_value": defaults.get(CONF_PLUG_ENTITY)}
        ): EntitySelector(EntitySelectorConfig(domain=["binary_sensor", "sensor"])),
        vol.Optional(
            CONF_LOCATION_ENTITY, description={"suggested_value": defaults.get(CONF_LOCATION_ENTITY)}
        ): EntitySelector(EntitySelectorConfig(domain=["device_tracker", "sensor"])),
    })


def _wallbox_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_WALLBOX_ENABLED, default=defaults.get(CONF_WALLBOX_ENABLED, True)): BooleanSelector(),
        vol.Optional(
            CONF_WB_POWER, description={"suggested_value": defaults.get(CONF_WB_POWER)}
        ): EntitySelector(EntitySelectorConfig(domain=["sensor", "number"])),
        vol.Optional(
            CONF_WB_STATE, description={"suggested_value": defaults.get(CONF_WB_STATE)}
        ): EntitySelector(EntitySelectorConfig(domain=["sensor", "binary_sensor"])),
        vol.Optional(
            CONF_WB_SESSION_ENERGY, description={"suggested_value": defaults.get(CONF_WB_SESSION_ENERGY)}
        ): EntitySelector(ENERGY_SENSOR),
        vol.Optional(
            CONF_WB_TOTAL_ENERGY, description={"suggested_value": defaults.get(CONF_WB_TOTAL_ENERGY)}
        ): EntitySelector(ENERGY_SENSOR),
        vol.Optional(
            CONF_WB_MAX_CURRENT, description={"suggested_value": defaults.get(CONF_WB_MAX_CURRENT)}
        ): EntitySelector(EntitySelectorConfig(domain=["number"])),
    })


def _settings_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_CAPACITY, default=defaults.get(CONF_CAPACITY, DEFAULT_CAPACITY)): NumberSelector(
            NumberSelectorConfig(min=20, max=150, step=0.5, unit_of_measurement="kWh", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_TARGET_SOC, default=defaults.get(CONF_TARGET_SOC, DEFAULT_TARGET_SOC)): NumberSelector(
            NumberSelectorConfig(min=50, max=100, step=1, unit_of_measurement="%")),
        vol.Required(CONF_PRICE_HOME, default=defaults.get(CONF_PRICE_HOME, DEFAULT_PRICE_HOME)): NumberSelector(
            NumberSelectorConfig(min=0, max=10, step=0.001, unit_of_measurement="€/kWh", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_PRICE_PUBLIC, default=defaults.get(CONF_PRICE_PUBLIC, DEFAULT_PRICE_PUBLIC)): NumberSelector(
            NumberSelectorConfig(min=0, max=10, step=0.001, unit_of_measurement="€/kWh", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_PRICE_SOLAR, default=defaults.get(CONF_PRICE_SOLAR, DEFAULT_PRICE_SOLAR)): NumberSelector(
            NumberSelectorConfig(min=0, max=10, step=0.001, unit_of_measurement="€/kWh", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_CHARGING_EFFICIENCY, default=defaults.get(CONF_CHARGING_EFFICIENCY, DEFAULT_EFFICIENCY * 100)): NumberSelector(
            NumberSelectorConfig(min=50, max=100, step=1, unit_of_measurement="%")),
        vol.Optional(CONF_SOLAR_ZONE, default=defaults.get(CONF_SOLAR_ZONE, DEFAULT_SOLAR_ZONE)): TextSelector(),
        vol.Required(CONF_POLL_INTERVAL, default=defaults.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)): NumberSelector(
            NumberSelectorConfig(min=10, max=300, step=5, unit_of_measurement="s")),
        vol.Required(CONF_TRIP_TIMEOUT, default=defaults.get(CONF_TRIP_TIMEOUT, DEFAULT_TRIP_TIMEOUT)): NumberSelector(
            NumberSelectorConfig(min=5, max=60, step=1, unit_of_measurement="min")),
        vol.Required(CONF_FUEL_ENABLED, default=defaults.get(CONF_FUEL_ENABLED, False)): BooleanSelector(),
        vol.Optional(CONF_FUEL_LABEL, default=defaults.get(CONF_FUEL_LABEL, DEFAULT_FUEL_LABEL)): TextSelector(),
        vol.Optional(CONF_FUEL_CONSUMPTION, default=defaults.get(CONF_FUEL_CONSUMPTION, DEFAULT_FUEL_CONSUMPTION)): NumberSelector(
            NumberSelectorConfig(min=1, max=20, step=0.1, unit_of_measurement="l/100km", mode=NumberSelectorMode.BOX)),
        vol.Optional(CONF_FUEL_PRICE, default=defaults.get(CONF_FUEL_PRICE, DEFAULT_FUEL_PRICE)): NumberSelector(
            NumberSelectorConfig(min=0.5, max=5, step=0.01, unit_of_measurement="€/l", mode=NumberSelectorMode.BOX)),
        vol.Optional(
            CONF_DIESEL_PRICE_ENTITY,
            description={"suggested_value": defaults.get(CONF_DIESEL_PRICE_ENTITY)},
        ): EntitySelector(EntitySelectorConfig(domain="sensor")),
        vol.Required(CONF_MAINT_ENABLED, default=defaults.get(CONF_MAINT_ENABLED, False)): BooleanSelector(),
        vol.Optional(CONF_TAG_TERMICO, default=defaults.get(CONF_TAG_TERMICO, DEFAULT_TAG_TERMICO)): NumberSelector(
            NumberSelectorConfig(min=0, max=1000, step=5, unit_of_measurement="€", mode=NumberSelectorMode.BOX)),
        vol.Optional(CONF_TAG_EV, default=defaults.get(CONF_TAG_EV, DEFAULT_TAG_EV)): NumberSelector(
            NumberSelectorConfig(min=0, max=1000, step=5, unit_of_measurement="€", mode=NumberSelectorMode.BOX)),
        vol.Optional(CONF_BOLLO_TERMICO, default=defaults.get(CONF_BOLLO_TERMICO, DEFAULT_BOLLO_TERMICO)): NumberSelector(
            NumberSelectorConfig(min=0, max=2000, step=5, unit_of_measurement="€/anno", mode=NumberSelectorMode.BOX)),
        vol.Optional(CONF_BOLLO_EV, default=defaults.get(CONF_BOLLO_EV, DEFAULT_BOLLO_EV)): NumberSelector(
            NumberSelectorConfig(min=0, max=2000, step=5, unit_of_measurement="€/anno", mode=NumberSelectorMode.BOX)),
        vol.Optional(CONF_TAGLIANDO_INTERVALLO, default=defaults.get(CONF_TAGLIANDO_INTERVALLO, DEFAULT_TAGLIANDO_INTERVALLO)): NumberSelector(
            NumberSelectorConfig(min=5000, max=50000, step=1000, unit_of_measurement="km", mode=NumberSelectorMode.BOX)),
        vol.Optional(CONF_NOTIFY_SERVICE, description={"suggested_value": defaults.get(CONF_NOTIFY_SERVICE, "")}): TextSelector(),
        vol.Optional(CONF_NOTIFY_DAYS, default=defaults.get(CONF_NOTIFY_DAYS, DEFAULT_NOTIFY_DAYS)): NumberSelector(
            NumberSelectorConfig(min=1, max=90, step=1, unit_of_measurement="gg")),
        vol.Optional(CONF_TAGLIANDO_MODE, default=defaults.get(CONF_TAGLIANDO_MODE, "km")): SelectSelector(
            SelectSelectorConfig(options=["km", "data"])),
        vol.Optional(CONF_TAGLIANDO_DATA, description={"suggested_value": defaults.get(CONF_TAGLIANDO_DATA, "")}): TextSelector(),
        vol.Optional(CONF_ASSICURAZIONE_COSTO, default=defaults.get(CONF_ASSICURAZIONE_COSTO, DEFAULT_ASSICURAZIONE_COSTO)): NumberSelector(
            NumberSelectorConfig(min=0, max=3000, step=10, unit_of_measurement="€/anno", mode=NumberSelectorMode.BOX)),
        vol.Optional(CONF_ASSICURAZIONE_DATA, description={"suggested_value": defaults.get(CONF_ASSICURAZIONE_DATA, "")}): TextSelector(),
        vol.Required(CONF_NOTIFY_CHARGE_START, default=defaults.get(CONF_NOTIFY_CHARGE_START, True)): BooleanSelector(),
        vol.Required(CONF_NOTIFY_CHARGE_END, default=defaults.get(CONF_NOTIFY_CHARGE_END, True)): BooleanSelector(),
        vol.Required(CONF_LOW_SOC_ENABLED, default=defaults.get(CONF_LOW_SOC_ENABLED, True)): BooleanSelector(),
        vol.Optional(CONF_LOW_SOC_THRESHOLD, default=defaults.get(CONF_LOW_SOC_THRESHOLD, DEFAULT_LOW_SOC_THRESHOLD)): NumberSelector(
            NumberSelectorConfig(min=5, max=80, step=1, unit_of_measurement="%")),
        vol.Optional(CONF_LOW_SOC_START, default=defaults.get(CONF_LOW_SOC_START, DEFAULT_LOW_SOC_START)): TextSelector(),
        vol.Optional(CONF_LOW_SOC_END, default=defaults.get(CONF_LOW_SOC_END, DEFAULT_LOW_SOC_END)): TextSelector(),
        vol.Required(CONF_CHARGE_SCHED_ENABLED, default=defaults.get(CONF_CHARGE_SCHED_ENABLED, False)): BooleanSelector(),
        vol.Optional(CONF_CHARGE_SCHED_MODE, default=defaults.get(CONF_CHARGE_SCHED_MODE, "orario")): SelectSelector(
            SelectSelectorConfig(options=["orario", "percentuale"])),
        vol.Optional(CONF_CHARGE_START_TIME, default=defaults.get(CONF_CHARGE_START_TIME, "23:30")): TextSelector(),
        vol.Optional(CONF_CHARGE_STOP_TIME, default=defaults.get(CONF_CHARGE_STOP_TIME, "07:00")): TextSelector(),
        vol.Optional(CONF_CHARGE_START_SOC, default=defaults.get(CONF_CHARGE_START_SOC, 30)): NumberSelector(
            NumberSelectorConfig(min=5, max=80, step=1, unit_of_measurement="%")),
        vol.Optional(CONF_CHARGE_STOP_SOC, default=defaults.get(CONF_CHARGE_STOP_SOC, 80)): NumberSelector(
            NumberSelectorConfig(min=50, max=100, step=1, unit_of_measurement="%")),
        vol.Optional(
            CONF_WB_CHARGE_SWITCH,
            description={"suggested_value": defaults.get(CONF_WB_CHARGE_SWITCH)},
        ): EntitySelector(EntitySelectorConfig(domain=["switch", "button"])),
        vol.Required(CONF_HAS_PV, default=defaults.get(CONF_HAS_PV, False)): BooleanSelector(),
        vol.Optional(
            CONF_BALANCE_GRID_SENSOR,
            description={"suggested_value": defaults.get(CONF_BALANCE_GRID_SENSOR)},
        ): EntitySelector(EntitySelectorConfig(domain="sensor")),
        vol.Optional(
            CONF_BALANCE_BATTERY_SENSOR,
            description={"suggested_value": defaults.get(CONF_BALANCE_BATTERY_SENSOR)},
        ): EntitySelector(EntitySelectorConfig(domain="sensor")),
        vol.Optional(CONF_BALANCE_INVERT_GRID, default=defaults.get(CONF_BALANCE_INVERT_GRID, False)): BooleanSelector(),
        vol.Optional(CONF_BALANCE_INCLUDE_BATTERY, default=defaults.get(CONF_BALANCE_INCLUDE_BATTERY, False)): BooleanSelector(),
        vol.Optional(CONF_BALANCE_WPA, default=defaults.get(CONF_BALANCE_WPA, DEFAULT_WPA)): NumberSelector(
            NumberSelectorConfig(min=100, max=1500, step=10, unit_of_measurement="W/A", mode=NumberSelectorMode.BOX)),
        vol.Optional(
            CONF_BALANCE_BATTERY_SOC_SENSOR,
            description={"suggested_value": defaults.get(CONF_BALANCE_BATTERY_SOC_SENSOR)},
        ): EntitySelector(EntitySelectorConfig(domain="sensor")),
        vol.Optional(CONF_BATTERY_PRIORITY_MIN, default=defaults.get(CONF_BATTERY_PRIORITY_MIN, DEFAULT_BATTERY_PRIORITY)): NumberSelector(
            NumberSelectorConfig(min=0, max=100, step=5, unit_of_measurement="%")),
        vol.Optional(
            CONF_CHARGE_TARGET_NUMBER,
            description={"suggested_value": defaults.get(CONF_CHARGE_TARGET_NUMBER)},
        ): EntitySelector(EntitySelectorConfig(domain="number")),
        vol.Optional(
            CONF_TEMP_ENTITY,
            description={"suggested_value": defaults.get(CONF_TEMP_ENTITY)},
        ): EntitySelector(EntitySelectorConfig(domain="sensor")),
        vol.Required(CONF_CO2_ENABLED, default=defaults.get(CONF_CO2_ENABLED, False)): BooleanSelector(),
        vol.Optional(CONF_CO2_THERMAL_GKM, default=defaults.get(CONF_CO2_THERMAL_GKM, DEFAULT_CO2_THERMAL_GKM)): NumberSelector(
            NumberSelectorConfig(min=50, max=300, step=5, unit_of_measurement="g/km", mode=NumberSelectorMode.BOX)),
        vol.Optional(CONF_CO2_GRID_GKWH, default=defaults.get(CONF_CO2_GRID_GKWH, DEFAULT_CO2_GRID_GKWH)): NumberSelector(
            NumberSelectorConfig(min=0, max=800, step=10, unit_of_measurement="g/kWh", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_SCADENZE_ENABLED, default=defaults.get(CONF_SCADENZE_ENABLED, False)): BooleanSelector(),
        vol.Optional(CONF_SCAD_BOLLO, description={"suggested_value": defaults.get(CONF_SCAD_BOLLO)}): TextSelector(),
        vol.Optional(CONF_SCAD_REVISIONE, description={"suggested_value": defaults.get(CONF_SCAD_REVISIONE)}): TextSelector(),
        vol.Optional(CONF_SCAD_ASSICURAZIONE, description={"suggested_value": defaults.get(CONF_SCAD_ASSICURAZIONE)}): TextSelector(),
    })


class RenaultMateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Wizard in tre passi."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(f"{DOMAIN}_{user_input[CONF_NAME].lower()}")
            self._abort_if_unique_id_configured()
            self._data.update(user_input)
            return await self.async_step_wallbox()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                **_car_schema({}).schema,
                vol.Required(CONF_MODEL, default=MODELS[0]): SelectSelector(
                    SelectSelectorConfig(options=MODELS)),
                vol.Required(CONF_CREATE_DASHBOARD, default=True): BooleanSelector(),
            }),
            errors=errors,
        )

    async def async_step_wallbox(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_settings()
        return self.async_show_form(step_id="wallbox", data_schema=_wallbox_schema({}))

    async def async_step_settings(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            eff = float(user_input.get(CONF_CHARGING_EFFICIENCY, DEFAULT_EFFICIENCY * 100))
            user_input[CONF_CHARGING_EFFICIENCY] = eff
            if not user_input.get(CONF_FUEL_ENABLED):
                user_input.pop(CONF_FUEL_LABEL, None)
                user_input.pop(CONF_FUEL_CONSUMPTION, None)
                user_input.pop(CONF_FUEL_PRICE, None)
                user_input.pop(CONF_DIESEL_PRICE_ENTITY, None)
            if not user_input.get(CONF_MAINT_ENABLED):
                for k in (CONF_TAG_TERMICO, CONF_TAG_EV, CONF_BOLLO_TERMICO,
                          CONF_BOLLO_EV, CONF_TAGLIANDO_INTERVALLO):
                    user_input.pop(k, None)
            if not user_input.get(CONF_CO2_ENABLED):
                for k in (CONF_CO2_THERMAL_GKM, CONF_CO2_GRID_GKWH):
                    user_input.pop(k, None)
            if not user_input.get(CONF_SCADENZE_ENABLED):
                for k in (CONF_SCAD_BOLLO, CONF_SCAD_REVISIONE, CONF_SCAD_ASSICURAZIONE):
                    user_input.pop(k, None)
            if not user_input.get(CONF_LOW_SOC_ENABLED):
                for k in (CONF_LOW_SOC_THRESHOLD, CONF_LOW_SOC_START, CONF_LOW_SOC_END):
                    user_input.pop(k, None)
            if not user_input.get(CONF_CHARGE_SCHED_ENABLED):
                for k in (CONF_CHARGE_SCHED_MODE, CONF_CHARGE_START_TIME, CONF_CHARGE_STOP_TIME,
                          CONF_CHARGE_START_SOC, CONF_CHARGE_STOP_SOC,
                          CONF_WB_CHARGE_SWITCH, CONF_CHARGE_TARGET_NUMBER):
                    user_input.pop(k, None)
            if not user_input.get(CONF_MAINT_ENABLED):
                user_input.pop(CONF_NOTIFY_SERVICE, None)
                user_input.pop(CONF_NOTIFY_DAYS, None)
                user_input.pop(CONF_TAGLIANDO_MODE, None)
                user_input.pop(CONF_TAGLIANDO_DATA, None)
                user_input.pop(CONF_ASSICURAZIONE_COSTO, None)
                user_input.pop(CONF_ASSICURAZIONE_DATA, None)
            self._data.update(user_input)
            return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)
        return self.async_show_form(step_id="settings", data_schema=_settings_schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return RenaultMateOptionsFlow(config_entry)


class RenaultMateOptionsFlow(config_entries.OptionsFlow):
    """Modifica entità e impostazioni dopo l'installazione."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        base = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                **_car_schema(base).schema,
                **_wallbox_schema(base).schema,
                **_settings_schema(base).schema,
            }),
        )
