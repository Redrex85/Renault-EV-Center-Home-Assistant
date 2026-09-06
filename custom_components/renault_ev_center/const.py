"""Costanti per Renault EV Center."""
from __future__ import annotations

DOMAIN = "renault_ev_center"
MANUFACTURER = "Renault EV Center"
PLATFORMS: list[str] = ["sensor", "binary_sensor", "button", "number", "select", "switch", "time"]

# --- chiavi config flow -------------------------------------------------------
CONF_NAME = "name"
CONF_ODOMETER = "odometer_entity"
CONF_BATTERY_LEVEL = "battery_level_entity"
CONF_RANGE = "range_entity"
CONF_CHARGING_ENTITY = "charging_entity"
CONF_PLUG_ENTITY = "plug_entity"
CONF_LOCATION_ENTITY = "location_entity"

CONF_WALLBOX_ENABLED = "wallbox_enabled"
CONF_WB_POWER = "wallbox_power_entity"
CONF_WB_STATE = "wallbox_state_entity"
CONF_WB_SESSION_ENERGY = "wallbox_session_energy_entity"
CONF_WB_TOTAL_ENERGY = "wallbox_total_energy_entity"
CONF_WB_MAX_CURRENT = "wallbox_max_current_entity"

CONF_CAPACITY = "battery_capacity"
CONF_TARGET_SOC = "target_soc"
CONF_PRICE_HOME = "price_home"
CONF_PRICE_PUBLIC = "price_public"
CONF_PRICE_SOLAR = "price_solar"
CONF_CHARGING_EFFICIENCY = "charging_efficiency"
CONF_POLL_INTERVAL = "poll_interval"
CONF_TRIP_TIMEOUT = "trip_timeout"

# confronto con auto termica (opzionale)
CONF_FUEL_ENABLED = "fuel_comparison"
CONF_FUEL_CONSUMPTION = "fuel_consumption"
CONF_FUEL_PRICE = "fuel_price"
CONF_FUEL_LABEL = "fuel_label"
CONF_DIESEL_PRICE_ENTITY = "diesel_price_entity"

# manutenzione e bollo (per il risparmio netto)
CONF_MAINT_ENABLED = "maint_comparison"
CONF_TAG_TERMICO = "service_cost_thermal"
CONF_TAG_EV = "service_cost_ev"
CONF_BOLLO_TERMICO = "road_tax_thermal"
CONF_BOLLO_EV = "road_tax_ev"
CONF_TAGLIANDO_INTERVALLO = "service_interval_km"
DEFAULT_TAG_TERMICO = 450.0
DEFAULT_TAG_EV = 80.0
DEFAULT_BOLLO_TERMICO = 350.0
DEFAULT_BOLLO_EV = 150.0
DEFAULT_TAGLIANDO_INTERVALLO = 15000

# notifiche scadenze
CONF_NOTIFY_SERVICE = "notify_service"
CONF_NOTIFY_DAYS = "notify_days"
CONF_TAGLIANDO_MODE = "tagliando_mode"
CONF_TAGLIANDO_DATA = "tagliando_data"
CONF_ASSICURAZIONE_COSTO = "assicurazione_costo"
CONF_ASSICURAZIONE_DATA = "assicurazione_data"
DEFAULT_NOTIFY_DAYS = 30
DEFAULT_ASSICURAZIONE_COSTO = 400.0

# dashboard automatica e modello auto
CONF_CREATE_DASHBOARD = "create_dashboard"
CONF_MODEL = "model"
MODELS = ["Megane E-Tech", "Scenic E-Tech", "Zoe", "Twingo E-Tech", "Alpine A290", "Custom"]

# notifiche e automazioni ricarica
CONF_NOTIFY_CHARGE_START = "notify_charge_start"
CONF_NOTIFY_CHARGE_END = "notify_charge_end"
CONF_LOW_SOC_ENABLED = "low_soc_enabled"
CONF_LOW_SOC_THRESHOLD = "low_soc_threshold"
CONF_LOW_SOC_START = "low_soc_start"
CONF_LOW_SOC_END = "low_soc_end"
CONF_CHARGE_SCHED_ENABLED = "charge_sched_enabled"
CONF_CHARGE_SCHED_MODE = "charge_sched_mode"  # orario | percentuale
CONF_CHARGE_START_TIME = "charge_start_time"
CONF_CHARGE_STOP_TIME = "charge_stop_time"
CONF_CHARGE_START_SOC = "charge_start_soc"
CONF_CHARGE_STOP_SOC = "charge_stop_soc"
CONF_CHARGE_START_BUTTON = "charge_start_button"
CONF_CHARGE_TARGET_NUMBER = "charge_target_number"
CONF_WB_CHARGE_SWITCH = "wb_charge_switch"
DEFAULT_LOW_SOC_THRESHOLD = 25.0
DEFAULT_LOW_SOC_START = "18:00"
DEFAULT_LOW_SOC_END = "22:00"

# profili installazione: minimal (solo auto) · pro (auto+wallbox) · enterprise (+FV)
CONF_HAS_PV = "has_pv"

# bilanciamento solare
CONF_BALANCE_GRID_SENSOR = "balance_grid_sensor"
CONF_BALANCE_BATTERY_SENSOR = "balance_battery_sensor"
CONF_BALANCE_INVERT_GRID = "balance_invert_grid"
CONF_BALANCE_INCLUDE_BATTERY = "balance_include_battery"
CONF_BALANCE_WPA = "balance_watts_per_amp"
CONF_BALANCE_BATTERY_SOC_SENSOR = "balance_battery_soc_sensor"
CONF_BATTERY_PRIORITY_MIN = "battery_priority_min"
DEFAULT_WPA = 230.0 * 3  # monofase 230 V ≈ 690 W/A
DEFAULT_MIN_AMPS = 6.0
DEFAULT_BATTERY_PRIORITY = 80.0
DEFAULT_MAX_AMPS = 16.0

# extra: meteo, CO2, scadenze
CONF_TEMP_ENTITY = "temp_entity"
CONF_CO2_ENABLED = "co2_comparison"
CONF_CO2_THERMAL_GKM = "co2_thermal_gkm"
CONF_CO2_GRID_GKWH = "co2_grid_gkwh"
CONF_SCADENZE_ENABLED = "scadenze_enabled"
CONF_SCAD_BOLLO = "scadenza_bollo"
CONF_SCAD_REVISIONE = "scadenza_revisione"
CONF_SCAD_ASSICURAZIONE = "scadenza_assicurazione"
DEFAULT_CO2_THERMAL_GKM = 120.0
DEFAULT_CO2_GRID_GKWH = 300.0

# zona considerata ricarica fotovoltaico/BEB ("beb", nome della tua zona...)
CONF_SOLAR_ZONE = "solar_zone"

# --- valori predefiniti -------------------------------------------------------
DEFAULT_NAME = "Renault"
DEFAULT_CAPACITY = 60.0
DEFAULT_TARGET_SOC = 80.0
DEFAULT_PRICE_HOME = 0.25
DEFAULT_PRICE_PUBLIC = 0.45
DEFAULT_PRICE_SOLAR = 0.0
DEFAULT_EFFICIENCY = 0.90
DEFAULT_POLL_INTERVAL = 30
DEFAULT_TRIP_TIMEOUT = 20
DEFAULT_FUEL_CONSUMPTION = 6.5
DEFAULT_FUEL_PRICE = 1.65
DEFAULT_FUEL_LABEL = "Diesel"
DEFAULT_SOLAR_ZONE = "beb"

CHARGE_STATE_ON_VALUES = {"on", "charging", "charge_in_progress"}
WALLBOX_CHARGING_STATES = {"charging"}

TRIP_MIN_KM = 0.5
TRIP_MIN_MINUTES = 2
