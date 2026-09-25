"""Coordinator Renault EV Center: legge le entità sorgente e gestisce motori e contatori."""
from __future__ import annotations

import asyncio
import csv
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CHARGE_STATE_ON_VALUES,
    PLUG_CONNECTED_VALUES,
    MESI_FILTRO,
    CONF_BATTERY_LEVEL,
    CONF_BOLLO_EV,
    CONF_BOLLO_TERMICO,
    CONF_CAPACITY,
    CONF_CHARGING_EFFICIENCY,
    CONF_CHARGING_ENTITY,
    CONF_CO2_ENABLED,
    CONF_GEOCODE_ENABLED,
    CONF_AVG_KMH,
    CONF_CO2_GRID_GKWH,
    CONF_CO2_THERMAL_GKM,
    CONF_DIESEL_PRICE_ENTITY,
    CONF_FUEL_CONSUMPTION,
    CONF_FUEL_ENABLED,
    CONF_FUEL_LABEL,
    CONF_FUEL_PRICE,
    CONF_LOCATION_ENTITY,
    CONF_MAINT_ENABLED,
    CONF_NAME,
    CONF_NOTIFY_DAYS,
    CONF_NOTIFY_SERVICE,
    CONF_ODOMETER,
    CONF_NOTIFY_CHARGE_START,
    CONF_NOTIFY_CHARGE_END,
    CONF_LOW_SOC_THRESHOLD,
    CONF_LOW_SOC_START,
    CONF_LOW_SOC_END,
    CONF_LOW_SOC_DAYS,
    DEFAULT_LOW_SOC_DAYS,
    WEEKDAYS,
    CONF_GSE_WPA,
    CONF_GSE_KW_MAX,
    CONF_GSE_KW_RIDOTTA,
    CONF_GSE_START,
    CONF_GSE_END,
    CONF_GSE_DOMENICA,
    CONF_GSE_HOLIDAY,
    DEFAULT_GSE_WPA,
    CONF_HOME_POWER_SENSOR,
    CONF_HOME_METER_KW,
    CONF_HOME_MAX_AMPS,
    CONF_HOME_REDUCE_AMPS,
    DEFAULT_HOME_METER_KW,
    DEFAULT_HOME_MAX_AMPS,
    DEFAULT_HOME_REDUCE_AMPS,
    DEFAULT_GSE_KW_MAX,
    DEFAULT_GSE_KW_RIDOTTA,
    DEFAULT_GSE_START,
    DEFAULT_GSE_END,
    CONF_CHARGE_SCHED_ENABLED,
    CONF_CHARGE_SCHED_MODE,
    CONF_CHARGE_START_TIME,
    CONF_CHARGE_STOP_TIME,
    CONF_CHARGE_START_SOC,
    CONF_CHARGE_STOP_SOC,
    CONF_CHARGE_START_BUTTON,
    CONF_AC_BUTTON,
    CONF_CHARGE_TARGET_NUMBER,
    CONF_WB_CHARGE_SWITCH,
    CONF_WB_STOP_SWITCH,
    CONF_BALANCE_GRID_SENSOR,
    CONF_BALANCE_BATTERY_SENSOR,
    CONF_BALANCE_INVERT_GRID,
    CONF_BALANCE_INCLUDE_BATTERY,
    CONF_BALANCE_BATTERY_SOC_SENSOR,
    CONF_BATTERY_PRIORITY_MIN,
    CONF_BALANCE_WPA,
DEFAULT_MAX_AMPS,
DEFAULT_MIN_AMPS,
DEFAULT_WB_START_W,
    DEFAULT_BATTERY_PRIORITY,
    CONF_PLUG_ENTITY,
    CONF_POLL_INTERVAL,
    CONF_PRICE_HOME,
    CONF_PRICE_PUBLIC,
    CONF_PRICE_SOLAR,
    CONF_PRE_KWH,
    CONF_PRE_EUR,
    CONF_INSTALL_ODO,
    CONF_RANGE,
    CONF_SCAD_ASSICURAZIONE,
    CONF_SCAD_BOLLO,
    CONF_SCAD_REVISIONE,
    CONF_SCADENZE_ENABLED,
    CONF_SOLAR_ZONE,
    CONF_TAG_EV,
    CONF_TAG_TERMICO,
    CONF_TAGLIANDO_DATA,
    CONF_TAGLIANDO_INTERVALLO,
    CONF_TYRE_INTERVAL,
    CONF_PURCHASE_DATE,
    CONF_TAGLIANDO_MODE,
    CONF_TARGET_SOC,
    CONF_ASSICURAZIONE_DATA,
    CONF_ASSICURAZIONE_COSTO,
    CONF_TEMP_ENTITY,
    CONF_TRIP_TIMEOUT,
    CONF_WALLBOX_ENABLED,
    CONF_WB_MAX_CURRENT,
    CONF_WB_POWER,
    CONF_WB_SESSION_ENERGY,
    CONF_WB_SESSION_TIME,
    CONF_WB_STATE,
    CONF_WB_TOTAL_ENERGY,
    DEFAULT_BOLLO_EV,
    DEFAULT_BOLLO_TERMICO,
    DEFAULT_CO2_GRID_GKWH,
    DEFAULT_CO2_THERMAL_GKM,
    DEFAULT_EFFICIENCY,
    DEFAULT_TAG_EV,
    DEFAULT_TAG_TERMICO,
    DEFAULT_TAGLIANDO_INTERVALLO,
    DEFAULT_ASSICURAZIONE_COSTO,
    DEFAULT_NOTIFY_DAYS,
    DOMAIN,
    MANUFACTURER,
    TRIP_MIN_KM,
    TRIP_MIN_MINUTES,
    WALLBOX_CHARGING_STATES,
)
from .meters import DeltaMeter, PeriodMeter, period_keys
from .store import MateStore
from .trip_engine import TripEngine, aggregate, group_by_day

_LOGGER = logging.getLogger(__name__)

PERIODS = ("daily", "weekly", "monthly", "yearly")


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _merge_history(history: list[dict], days_grouped: list[dict]) -> list[dict]:
    """Unisce giornate da metri (kwh/pct) e da viaggi (km/eff) per lo storico."""
    hist_map: dict[str, dict] = {}
    for d in history:
        key = d.get("data")
        if key:
            hist_map.setdefault(key, {}).update(d)
    for dg in days_grouped:
        key = dg.get("data")
        if not key:
            continue
        row = hist_map.setdefault(key, {"data": key})
        row["km"] = dg.get("km", row.get("km", 0.0))
        row["kwh"] = dg.get("kwh", row.get("kwh", 0.0))
        if dg.get("kwh_per_100km") is not None:
            row["kwh_per_100km"] = dg["kwh_per_100km"]
        row["n_trip"] = dg.get("n_trip", 0)
    return sorted(hist_map.values(), key=lambda r: r.get("data") or "")[-365:]


def _in_window(hhmm: str, start: str, stop: str) -> bool:
    if start <= stop:
        return start <= hhmm < stop
    return hhmm >= start or hhmm < stop


def _best_measured_delta(pairs):
    """Maggiore tra i delta misurati di una ricarica.

    Ogni coppia è (inizio, fine) di un contatore. I delta negativi vengono scartati:
    il contatore azzerato a metà sessione (es. reset di mezzanotte) non è una misura valida.
    """
    vals = [fine - inizio for inizio, fine in pairs
            if inizio is not None and fine is not None and fine >= inizio]
    return max(vals) if vals else 0.0


def _ac_dc_from_power(power_max_kw, power_avg_kw=0.0):
    """AC o DC dalla potenza: oltre 22 kW (3 fasi 32 A) è DC/fast. None se non nota."""
    p = _f(power_max_kw) or _f(power_avg_kw) or 0.0
    if p <= 0:
        return None
    return "DC" if p > 22.0 else "AC"


def _charge_energy(measured: float, accum: float, tipo: str, soc_start, battery, capacity):
    """Energia di una ricarica, in ordine di affidabilità.

    1. delta dei contatori wallbox (misura vera, kWh);
    2. integrale della potenza istantanea wallbox accumulato durante la sessione;
    3. stima dal SoC — solo fuori casa (per le colonnine pubbliche è la via normale).

    Ritorna (kWh, origine): origine None se misurata, altrimenti
    "potenza_istantanea", "fuori_casa" o "casa_senza_misura" (ripiego da segnalare).
    """
    if measured > 0:
        return measured, None
    if _f(accum) > 0.05:
        return _f(accum), "potenza_istantanea"
    delta = max(_f(battery) - _f(soc_start), 0.0)
    kwh = delta * _f(capacity, 60.0) / 100.0
    return kwh, "fuori_casa" if tipo != "Casa" else "casa_senza_misura"


def _num(hass: HomeAssistant, entity_id: str | None, default: float = 0.0) -> float:
    if not entity_id:
        return default
    st = hass.states.get(entity_id)
    if st is None or st.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        return default
    return _f(st.state, default)


def _txt(hass: HomeAssistant, entity_id: str | None) -> str:
    if not entity_id:
        return ""
    st = hass.states.get(entity_id)
    if st is None:
        return ""
    return str(st.state)


def _unit(hass: HomeAssistant, entity_id: str | None) -> str:
    if not entity_id:
        return ""
    st = hass.states.get(entity_id)
    if st is None:
        return ""
    return str(st.attributes.get("unit_of_measurement", ""))


def _new_cost_meter() -> dict[str, Any]:
    return {"key": "", "value": 0.0, "last": 0.0}


class RenaultMateCoordinator(DataUpdateCoordinator):
    """Raccoglie i dati dalle entità selezionate e calcola tutto il resto."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        opts = {**entry.data, **entry.options}
        self.entry = entry
        self.opts = opts
        self.geocode_enabled = bool(opts.get(CONF_GEOCODE_ENABLED, True))
        self._geocode_backfilled = False
        self.purchase_date = str(opts.get(CONF_PURCHASE_DATE) or "")
        self.store = MateStore(hass, entry.entry_id)

        self.capacity = _f(opts.get(CONF_CAPACITY), 60.0) or 60.0
        self.target_soc = _f(opts.get(CONF_TARGET_SOC), 80.0)
        self.price_home = _f(opts.get(CONF_PRICE_HOME), 0.25)
        self.price_public = _f(opts.get(CONF_PRICE_PUBLIC), 0.45)
        self.price_solar = _f(opts.get(CONF_PRICE_SOLAR), 0.0)
        self.charging_eff = (_f(opts.get(CONF_CHARGING_EFFICIENCY), DEFAULT_EFFICIENCY) or 90) / 100.0
        self.solar_zone = str(opts.get(CONF_SOLAR_ZONE) or "").lower()
        self.fuel_enabled = bool(opts.get(CONF_FUEL_ENABLED))
        self.fuel_label = str(opts.get(CONF_FUEL_LABEL) or "Diesel")
        self.fuel_consumption = _f(opts.get(CONF_FUEL_CONSUMPTION), 6.5)
        self.fuel_price = _f(opts.get(CONF_FUEL_PRICE), 1.65)
        self.diesel_price_entity = opts.get(CONF_DIESEL_PRICE_ENTITY) or ""
        self.maint_enabled = bool(opts.get(CONF_MAINT_ENABLED))
        self.tag_termico = _f(opts.get(CONF_TAG_TERMICO), 250.0)
        self.tag_ev = _f(opts.get(CONF_TAG_EV), 80.0)
        self.bollo_termico = _f(opts.get(CONF_BOLLO_TERMICO), 350.0)
        self.bollo_ev = _f(opts.get(CONF_BOLLO_EV), 150.0)
        self.tagliando_intervallo = max(_f(opts.get(CONF_TAGLIANDO_INTERVALLO), 15000), 5000)
        self.tyre_interval = max(_f(opts.get(CONF_TYRE_INTERVAL), 40000), 5000)
        self.temp_entity = opts.get(CONF_TEMP_ENTITY) or ""
        self.co2_enabled = bool(opts.get(CONF_CO2_ENABLED))
        self.co2_thermal_gkm = _f(opts.get(CONF_CO2_THERMAL_GKM), 120.0)
        self.co2_grid_gkwh = _f(opts.get(CONF_CO2_GRID_GKWH), 300.0)
        self.scadenze_enabled = bool(opts.get(CONF_SCADENZE_ENABLED))
        self.scad_bollo = str(opts.get(CONF_SCAD_BOLLO) or "")
        self.scad_revisione = str(opts.get(CONF_SCAD_REVISIONE) or "")
        self.scad_assicurazione = str(opts.get(CONF_SCAD_ASSICURAZIONE) or "")
        self.notify_service = str(opts.get(CONF_NOTIFY_SERVICE) or "")
        # versione dell'integrazione (impostata da async_setup_entry, fuori dall'event loop):
        # usata dagli attributi dei sensori per l'auto-refresh della card
        self.version = ""
        self.notify_days = int(_f(opts.get(CONF_NOTIFY_DAYS), 30))
        self.tagliando_mode = str(opts.get(CONF_TAGLIANDO_MODE) or "km")
        self.tagliando_data = str(opts.get(CONF_TAGLIANDO_DATA) or "")
        self.assicurazione_costo = _f(opts.get(CONF_ASSICURAZIONE_COSTO), 400.0)

        # vampire drain: SoC persa da fermo (non in carica, odometro fermo)
        self.drain_meter = DeltaMeter("down")
        self.drain_mesi = DeltaMeter("down")
        self._drain_odom_ref: float | None = None

        # notifiche / automazioni ricarica
        self.notify_charge_start = bool(opts.get(CONF_NOTIFY_CHARGE_START, True))
        self.notify_charge_end = bool(opts.get(CONF_NOTIFY_CHARGE_END, True))
        self.low_soc_threshold = _f(opts.get(CONF_LOW_SOC_THRESHOLD), 25.0)
        self.low_soc_start = str(opts.get(CONF_LOW_SOC_START) or "18:00")
        self.low_soc_end = str(opts.get(CONF_LOW_SOC_END) or "22:00")
        _days = opts.get(CONF_LOW_SOC_DAYS)
        self.low_soc_days = [str(d) for d in _days] if isinstance(_days, (list, tuple)) and _days \
            else list(DEFAULT_LOW_SOC_DAYS)
        # --- sperimentazione GSE -------------------------------------------------
        self.gse_wpa = max(_f(opts.get(CONF_GSE_WPA), DEFAULT_GSE_WPA), 1.0)
        self.gse_kw_max = _f(opts.get(CONF_GSE_KW_MAX), DEFAULT_GSE_KW_MAX)
        self.gse_kw_ridotta = _f(opts.get(CONF_GSE_KW_RIDOTTA), DEFAULT_GSE_KW_RIDOTTA)
        self.gse_start = str(opts.get(CONF_GSE_START) or DEFAULT_GSE_START)
        self.gse_end = str(opts.get(CONF_GSE_END) or DEFAULT_GSE_END)
        self.gse_domenica = bool(opts.get(CONF_GSE_DOMENICA, True))
        self.gse_holiday = str(opts.get(CONF_GSE_HOLIDAY) or "")
        # --- bilanciamento casalingo ---------------------------------------------
        self.home_power_sensor = str(opts.get(CONF_HOME_POWER_SENSOR) or "")
        self.home_meter_kw = _f(opts.get(CONF_HOME_METER_KW), DEFAULT_HOME_METER_KW)
        self.home_max_amps = _f(opts.get(CONF_HOME_MAX_AMPS), DEFAULT_HOME_MAX_AMPS)
        self.home_reduce_amps = _f(opts.get(CONF_HOME_REDUCE_AMPS), DEFAULT_HOME_REDUCE_AMPS)
        self._home_hi_since: float | None = None
        self._auto_restored = False
        self._last_pos_loc = ""
        self._home_lo_since: float | None = None
        self._home_last: dict[str, Any] = {}
        self.charge_sched_enabled = bool(opts.get(CONF_CHARGE_SCHED_ENABLED, False))
        self.charge_sched_mode = str(opts.get(CONF_CHARGE_SCHED_MODE) or "orario")
        self.charge_start_time = str(opts.get(CONF_CHARGE_START_TIME) or "23:30")
        self.charge_stop_time = str(opts.get(CONF_CHARGE_STOP_TIME) or "07:00")
        self.charge_start_soc = _f(opts.get(CONF_CHARGE_START_SOC), 30.0)
        self.charge_stop_soc = _f(opts.get(CONF_CHARGE_STOP_SOC), 80.0)
        self.charge_start_button = opts.get(CONF_WB_CHARGE_SWITCH) or ""
        # entità di STOP dedicata (switch/button): senza, con un button si ripremeva l'avvio
        self.wb_stop_switch = opts.get(CONF_WB_STOP_SWITCH) or ""
        self.charge_target_number = opts.get(CONF_CHARGE_TARGET_NUMBER) or ""
        self._sched_done_key = ""
        self.balance_grid_sensor = opts.get(CONF_BALANCE_GRID_SENSOR) or ""
        self.balance_battery_sensor = opts.get(CONF_BALANCE_BATTERY_SENSOR) or ""
        self.balance_invert_grid = bool(opts.get(CONF_BALANCE_INVERT_GRID, False))
        self.balance_include_battery = bool(opts.get(CONF_BALANCE_INCLUDE_BATTERY, False))
        self.balance_wpa = max(_f(opts.get(CONF_BALANCE_WPA), 690.0), 100.0)
        self.balance_battery_soc_sensor = opts.get(CONF_BALANCE_BATTERY_SOC_SENSOR) or ""
        self.battery_priority_min = _f(opts.get(CONF_BATTERY_PRIORITY_MIN), 80.0)
        self._balance_last_change = 0.0

        # fallback di configurazione: i number creati dall'integrazione hanno la precedenza
        self._cfg_capacity = self.capacity
        self._cfg_target_soc = self.target_soc
        self._cfg_price_home = self.price_home
        self._cfg_price_public = self.price_public
        self._cfg_price_solar = self.price_solar
        self.setting_ids: dict[str, str] = {}

        # --- contatori km -----------------------------------------------------
        self.km_meters: dict[str, PeriodMeter] = {
            p: PeriodMeter() for p in PERIODS
        }
        # --- energia caricata dalla wallbox ------------------------------------
        self.wb_meters: dict[str, DeltaMeter] = {p: DeltaMeter("up") for p in PERIODS}
        # --- costi ricarica per periodo -----------------------------------------
        self.cost_meters: dict[str, dict[str, Any]] = {p: _new_cost_meter() for p in PERIODS}
        self.cost_total = 0.0
        # --- batteria % e kWh carica/scarica ------------------------------------
        self.pct_daily = {"up": DeltaMeter("up"), "down": DeltaMeter("down")}
        self.kwh_meters: dict[str, dict[str, DeltaMeter]] = {
            p: {"up": DeltaMeter("up"), "down": DeltaMeter("down")} for p in PERIODS
        }

        # --- motore viaggi ------------------------------------------------------
        self.trip = TripEngine(
            timeout_minuti=int(_f(opts.get(CONF_TRIP_TIMEOUT), 20)),
            min_km=TRIP_MIN_KM,
            min_minutes=TRIP_MIN_MINUTES,
            capacity_kwh=self.capacity,
            tz=dt_util.DEFAULT_TIME_ZONE,
            avg_kmh=_f(opts.get(CONF_AVG_KMH), 30.0) or 30.0,
        )

        # --- stato sessione di ricarica ------------------------------------------
        self.charge_session: dict[str, Any] | None = None
        self._wb_sess_start: float | None = None
        self._wb_sess_time = 0.0
        self._charge_off_polls = 0
        self._wb_counter_ref: float | None = None

        # --- storico giornaliero --------------------------------------------------
        self.today_rec: dict[str, Any] = {}

        self._last_save = 0.0
        self._last_inputs: tuple | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(
                seconds=int(_f(opts.get(CONF_POLL_INTERVAL), 30)) or 30
            ),
        )

    # ------------------------------------------------------------------ device
    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=str(self.opts.get("name", "Renault EV")),
            manufacturer=MANUFACTURER,
            model="Renault E-Tech elettrica",
        )

    # ------------------------------------------------------------------- store
    async def async_load_store(self) -> None:
        await self.store.async_load()
        counters = self.store.data["counters"]
        # scadenze dinamiche: inizializza dal config la prima volta
        scad = self.store.data.setdefault("scadenze", {})
        if not scad.get("assicurazione") and self.scad_assicurazione:
            scad["assicurazione"] = self.scad_assicurazione
        if not scad.get("bollo") and self.scad_bollo:
            scad["bollo"] = self.scad_bollo
        if not scad.get("revisione") and self.scad_revisione:
            scad["revisione"] = self.scad_revisione
        if not scad.get("tagliando_data") and self.tagliando_data:
            scad["tagliando_data"] = self.tagliando_data
        if not scad.get("tagliando_mode"):
            scad["tagliando_mode"] = self.tagliando_mode
        # P1-2: save atomico allo shutdown
        self.entry.async_on_unload(
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._async_save_on_stop)
        )
        for p in PERIODS:
            self.km_meters[p] = PeriodMeter.from_dict(counters.get(f"km_{p}"))
            self.wb_meters[p] = DeltaMeter.from_dict(counters.get(f"wb_{p}"), "up")
            cm = counters.get(f"cost_{p}")
            m = _new_cost_meter()
            if isinstance(cm, dict):
                m.update({k: cm.get(k, v) for k, v in m.items()})
            self.cost_meters[p] = m
            self.kwh_meters[p] = {
                "up": DeltaMeter.from_dict(counters.get(f"kwh_{p}_up"), "up"),
                "down": DeltaMeter.from_dict(counters.get(f"kwh_{p}_down"), "down"),
            }
        self.pct_daily = {
            "up": DeltaMeter.from_dict(counters.get("pct_up"), "up"),
            "down": DeltaMeter.from_dict(counters.get("pct_down"), "down"),
        }
        self.drain_meter = DeltaMeter.from_dict(counters.get("drain_down"), "down")
        self.drain_mesi = DeltaMeter.from_dict(counters.get("drain_month_down"), "down")
        # costo totale = somma delle ricariche registrate (fonte di verità).
        # Ricalcolato anche qui: i record già presenti non devono restare fuori dal totale.
        _somma_costi = round(sum(_f(c.get("costo")) for c in self.store.data["charges"]), 2)
        self.cost_total = _somma_costi or _f(counters.get("cost_total"), 0.0)
        if isinstance(counters.get("trip"), dict):
            self.trip.restore(counters["trip"])
            # un viaggio non sopravvive al riavvio: evita "in movimento" fantasma
            self.trip.active = False
        self.today_rec = counters.get("today_rec") or {}

    async def _async_save_on_stop(self, event) -> None:  # noqa: ARG002
        # salvataggio atomico sincrono allo shutdown
        try:
            c: dict[str, Any] = {"cost_total": round(self.cost_total, 4),
                                 "trip": self.trip.dump(), "today_rec": self.today_rec}
            for p in PERIODS:
                c[f"km_{p}"] = self.km_meters[p].to_dict()
                c[f"wb_{p}"] = self.wb_meters[p].to_dict()
                c[f"cost_{p}"] = self.cost_meters[p]
                c[f"kwh_{p}_up"] = self.kwh_meters[p]["up"].to_dict()
                c[f"kwh_{p}_down"] = self.kwh_meters[p]["down"].to_dict()
            c["pct_up"] = self.pct_daily["up"].to_dict()
            c["pct_down"] = self.pct_daily["down"].to_dict()
            c["drain_down"] = self.drain_meter.to_dict()
            c["drain_month_down"] = self.drain_mesi.to_dict()
            self.store.data.setdefault("counters", {}).update(c)
            await self.store._store.async_save(self.store.data["counters"] | {"trips": self.store.data["trips"][-2000:], "charges": self.store.data["charges"][-2000:], "daily": self.store.data["daily"][-365:], "health": self.store.data.get("health", {}), "maintenance": self.store.data.get("maintenance", [])[-200:], "monthly_km": self.store.data.get("monthly_km", {}), "scadenze": self.store.data.get("scadenze", {})})
        except Exception:  # noqa: BLE001
            pass

    def persist(self, force: bool = False) -> None:
        now = time.time()
        # salvataggio periodico ogni 15 min (i viaggi/ricariche si salvano subito con force=True)
        if not force and (now - self._last_save) < 900:
            return
        self._last_save = now
        c: dict[str, Any] = {"cost_total": round(self.cost_total, 4),
                             "trip": self.trip.dump(), "today_rec": self.today_rec}
        for p in PERIODS:
            c[f"km_{p}"] = self.km_meters[p].to_dict()
            c[f"wb_{p}"] = self.wb_meters[p].to_dict()
            c[f"cost_{p}"] = self.cost_meters[p]
            c[f"kwh_{p}_up"] = self.kwh_meters[p]["up"].to_dict()
            c[f"kwh_{p}_down"] = self.kwh_meters[p]["down"].to_dict()
        c["pct_up"] = self.pct_daily["up"].to_dict()
        c["pct_down"] = self.pct_daily["down"].to_dict()
        c["drain_down"] = self.drain_meter.to_dict()
        c["drain_month_down"] = self.drain_mesi.to_dict()
        self.store.data.setdefault("counters", {}).update(c)
        self.store.save()

    # ------------------------------------------------------------------ helpers
    def register_setting(self, kind: str, key: str, entity_id: str) -> None:
        """Le piattaforme number/select registrano qui le proprie entità."""
        self.setting_ids[f"{kind}.{key}"] = entity_id

    def _setting_num(self, key: str, fallback: float) -> float:
        entity_id = self.setting_ids.get(f"number.{key}")
        if entity_id:
            st = self.hass.states.get(entity_id)
            if st is not None and st.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                try:
                    return float(st.state)
                except (TypeError, ValueError):
                    pass
        return fallback

    def _setting_opt(self, key: str, fallback: str) -> str:
        entity_id = self.setting_ids.get(f"select.{key}")
        if entity_id:
            st = self.hass.states.get(entity_id)
            if st is not None and st.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                return st.state
        return fallback

    def _setting_time(self, key: str, fallback: str) -> str:
        """Legge un'entità time ("HH:MM:SS") e la riduce a "HH:MM"."""
        entity_id = self.setting_ids.get(f"time.{key}")
        if entity_id:
            st = self.hass.states.get(entity_id)
            if st is not None and st.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                parts = st.state.split(":")
                if len(parts) >= 2:
                    return f"{parts[0]}:{parts[1]}"
        return fallback

    def _apply_number_settings(self) -> None:
        self.capacity = self._setting_num("capacity", self._cfg_capacity) or self._cfg_capacity
        self.target_soc = self._setting_num("target", self._cfg_target_soc)
        self.price_home = self._setting_num("price_home", self._cfg_price_home)
        self.price_public = self._setting_num("price_public", self._cfg_price_public)
        self.price_solar = self._setting_num("price_solar", self._cfg_price_solar)
        self.assicurazione_costo = self._setting_num("assic_costo", self.assicurazione_costo)
        self.trip.capacity_kwh = self._eff_capacity()

    def _eff_capacity(self) -> float:
        """Capacità EFFETTIVA = capacità nominale × SOH ufficiale (es. 60 × 0,94 = 56,4 kWh).

        È la base giusta per convertire il SoC in kWh: 1% = capacità_eff / 100
        (col SOH 94% → 0,564 kWh invece di 0,6).
        """
        soh = max(self._setting_num("soh_official", 100.0), 40.0)
        return (self.capacity or 60.0) * (soh / 100.0)

    def _read_temp(self) -> float | None:
        """Temperatura esterna: dal sensore mappato; se manca/unknown ripiega su un'entità
        `weather` (es. weather.forecast_casa, attributo `temperature`). Meglio di niente.
        """
        ent = self.temp_entity
        if ent:
            st = self.hass.states.get(ent)
            if st is not None and st.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                if str(ent).split(".")[0] == "weather":
                    v = st.attributes.get("temperature")
                    if v is not None:
                        return _f(v, None)
                else:
                    return _f(st.state, None)
        # ripiego: prima weather.forecast_casa, poi il primo weather con temperatura
        cands: list = []
        f = self.hass.states.get("weather.forecast_casa")
        if f is not None:
            cands.append(f)
        cands += [s for s in self.hass.states.async_all("weather") if s is not f]
        for st in cands:
            v = st.attributes.get("temperature")
            if v is not None:
                return _f(v, None)
        return None

    def _automation_sig(self) -> tuple:
        return (
            self.capacity,
            self.target_soc,
            self.price_home,
            self.price_public,
            self.price_solar,
            self.assicurazione_costo,
            self._switch_on("notify_start"),
            self._switch_on("notify_end"),
            self._switch_on("low_soc"),
            self._switch_on("charge_sched"),
            self._switch_on("balance"),
            self._setting_num("soh_official", 100.0),
            self._setting_num("low_soc", self.low_soc_threshold),
            self._setting_num("charge_start_soc", self.charge_start_soc),
            self._setting_num("charge_stop_soc", self.charge_stop_soc),
            self._setting_num("balance_min_amps", DEFAULT_MIN_AMPS),
            self._setting_num("balance_max_amps", DEFAULT_MAX_AMPS),
            self._setting_num("battery_priority", self.battery_priority_min),
            self._setting_time("charge_start_time", self.charge_start_time),
            self._setting_time("charge_stop_time", self.charge_stop_time),
            self._setting_time("low_soc_start", self.low_soc_start),
            self._setting_time("low_soc_end", self.low_soc_end),
            self._setting_opt("charge_sched_mode", self.charge_sched_mode),
            self._setting_opt("filtro_tipo", "Tutte"),
            self._setting_opt("filtro_periodo", "Mese"),
            self._setting_opt("filtro_anno", "Tutti"),
        )

    def _prezzo_termico(self) -> float:
        """Prezzo carburante: sensore live se configurato, altrimenti il number dell'integrazione.

        FONTE UNICA: `number.<auto>_prezzo_carburante`. Prima il coordinator usava il valore
        fisso di configurazione mentre il pannello leggeva un altro valore (localStorage):
        due prezzi diversi → risparmi incoerenti.
        """
        if self.diesel_price_entity:
            st = self.hass.states.get(self.diesel_price_entity)
            if st is not None and st.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                v = _f(st.state, 0.0)
                if v > 0.2:
                    return v
        return self._setting_num("fuel_price", self.fuel_price)

    def _price_for_zone(self, zone: str) -> float:
        z = (zone or "").lower()
        if z == "home":
            return self.price_home
        if self.solar_zone and z == self.solar_zone:
            return self.price_solar
        return self.price_public

    @staticmethod
    def _is_charging(value: str) -> bool:
        v = (value or "").lower()
        return v in CHARGE_STATE_ON_VALUES

    def _plug_connected(self) -> bool | None:
        """Spina dell'auto collegata? True/False, None se l'entità manca o è ignota."""
        ent = self.opts.get(CONF_PLUG_ENTITY)
        if not ent:
            return None
        v = (_txt(self.hass, ent) or "").lower()
        if not v or v in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        return v in PLUG_CONNECTED_VALUES

    def _wb_counter(self) -> float | None:
        sess = self.opts.get(CONF_WB_SESSION_ENERGY)
        tot = self.opts.get(CONF_WB_TOTAL_ENERGY)
        if sess:
            st = self.hass.states.get(sess)
            if st is not None and st.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                return _f(st.state)
        if tot:
            st = self.hass.states.get(tot)
            if st is not None and st.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                return _f(st.state)
        return None

    def _wb_total_counter(self) -> float | None:
        """Contatore energia TOTALE wallbox (indipendente dalla sessione)."""
        tot = self.opts.get(CONF_WB_TOTAL_ENERGY)
        if not tot:
            return None
        st = self.hass.states.get(str(tot))
        if st is None or st.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        return _f(st.state)

    def _wb_power_kw(self) -> float:
        entity = self.opts.get(CONF_WB_POWER)
        val = _num(self.hass, entity, 0.0)
        unit = _unit(self.hass, entity).lower()
        if unit == "w":
            val = val / 1000.0
        return max(val, 0.0)

    def _compute_heavy(self, trips, charges, daily, today_key, keys, now):
        """Calcoli pesanti O(n) eseguiti fuori dall'event loop."""
        cutoff7 = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        cutoff30 = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        cutoff90 = (now - timedelta(days=90)).strftime("%Y-%m-%d")
        t7 = [t for t in trips if t.get("data", "") >= cutoff7]
        t30 = [t for t in trips if t.get("data", "") >= cutoff30]
        t90 = [t for t in trips if t.get("data", "") >= cutoff90]
        trips_oggi_list = [t for t in trips if t.get("data") == today_key]
        charges_oggi = [c for c in charges if c.get("data") == today_key]
        mese_key = keys["monthly"]
        charges_mese = [c for c in charges if str(c.get("data", ""))[:7] == mese_key]
        stats_all = aggregate(trips)
        best_eff = 0.0
        for t in trips:
            e = _f(t.get("kwh_per_100km"))
            if e > 0 and (best_eff == 0 or e < best_eff):
                best_eff = e
        rotte: dict[str, dict[str, float]] = {}
        for t in trips:
            key = "%s → %s" % (t.get("zona_partenza", "?"), t.get("zona_arrivo", "?"))
            r = rotte.setdefault(key, {"n": 0, "km": 0.0, "kwh": 0.0})
            r["n"] = int(r["n"]) + 1
            r["km"] += _f(t.get("km"))
            r["kwh"] += _f(t.get("kwh_consumati"))
        zone_routes = []
        for key, r in rotte.items():
            eff = round(r["kwh"] / r["km"] * 100, 2) if r["km"] > 0 else 0.0
            zone_routes.append({
                "rotta": key, "n": int(r["n"]), "km": round(r["km"], 1),
                "kwh": round(r["kwh"], 2),
                "eff": eff,
                "km_medio": round(r["km"] / int(r["n"]), 1) if int(r["n"]) else 0.0,
                "costo": round(r["kwh"] * self.price_home, 2),
            })
        zone_routes.sort(key=lambda z: z["km"], reverse=True)
        valutabili = [z for z in zone_routes if z["eff"] > 0]
        zone_best = min(valutabili, key=lambda z: z["eff"], default=None)
        zone_worst = max(valutabili, key=lambda z: z["eff"], default=None)
        mese_trips = [
            t for t in trips
            if str(t.get("data", ""))[:7] == mese_key
            and _f(t.get("km")) >= 1 and _f(t.get("kwh_per_100km")) > 0
        ]
        best_trip = min(mese_trips, key=lambda t: _f(t.get("kwh_per_100km")), default=None)
        worst_trip = max(mese_trips, key=lambda t: _f(t.get("kwh_per_100km")), default=None)
        return {
            "t7": t7, "t30": t30, "t90": t90,
            "trips_oggi_list": trips_oggi_list,
            "charges_oggi": charges_oggi, "charges_mese": charges_mese,
            "stats_all": stats_all, "best_eff": best_eff,
            "zone_routes": zone_routes, "zone_best": zone_best, "zone_worst": zone_worst,
            "best_trip": best_trip, "worst_trip": worst_trip,
        }

    # -------------------------------------------------------------------- tick

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self._async_update_data_inner()
        except UpdateFailed:
            raise
        except Exception as err:  # noqa: BLE001
            if self.data:
                _LOGGER.warning("Update fallito, uso dati precedenti: %s", err, exc_info=True)
                return self.data
            raise UpdateFailed(f"Aggiornamento Renault EV Center fallito: {err}") from err
        # eco polling: intervallo breve se auto attiva (viaggio/ricarica), lungo se ferma
        self.update_interval = timedelta(seconds=self._eco_interval(data))
        return data

    def _eco_interval(self, data: dict[str, Any]) -> int:
        """Polling intelligente: rapido quando attiva, lento quando ferma."""
        base = int(_f(self.opts.get(CONF_POLL_INTERVAL), 30)) or 30
        active = bool((data.get("trip") or {}).get("active")) or self.charge_session is not None
        return max(base, 15) if active else max(base * 4, 120)

    def start_source_listeners(self):
        """Reattività: aggiorna subito al cambio di una entità sorgente."""
        o = self.opts
        ids = [
            o.get(CONF_ODOMETER), o.get(CONF_BATTERY_LEVEL), o.get(CONF_RANGE),
            o.get(CONF_CHARGING_ENTITY), o.get(CONF_PLUG_ENTITY), o.get(CONF_LOCATION_ENTITY),
            o.get(CONF_WB_POWER), o.get(CONF_WB_STATE),
        ]
        ids = [i for i in ids if i]
        if not ids:
            return lambda: None
        return async_track_state_change_event(self.hass, ids, self._on_source_change)

    async def _on_source_change(self, event) -> None:  # noqa: ARG002
        # debounced dal coordinator: evita raffiche di aggiornamenti
        await self.async_request_refresh()

    async def _async_update_data_inner(self) -> dict[str, Any]:
        hass = self.hass
        now = dt_util.now()
        keys = period_keys(now)
        o = self.opts

        odometer = _num(hass, o.get(CONF_ODOMETER))
        battery = _num(hass, o.get(CONF_BATTERY_LEVEL))
        rng = _num(hass, o.get(CONF_RANGE))
        charging_raw = _txt(hass, o.get(CONF_CHARGING_ENTITY))
        plug = _txt(hass, o.get(CONF_PLUG_ENTITY)).lower()
        location = (_txt(hass, o.get(CONF_LOCATION_ENTITY)) or "").lower()
        charging = self._is_charging(charging_raw)

        wb_enabled = bool(o.get(CONF_WALLBOX_ENABLED))
        wb_power = self._wb_power_kw() if wb_enabled else 0.0
        wb_state = _txt(hass, o.get(CONF_WB_STATE)).lower() if wb_enabled else ""
        # L'energia della wallbox è della NOSTRA auto solo con la spina collegata:
        # una wallbox può erogare verso un'altra macchina (la Renault è a casa ferma
        # e scollegata) → quella corrente non va conteggiata né come kWh né come costo.
        # None (entità spina non configurata) = nessun vincolo, come prima.
        plug_ours = self._plug_connected() is not False

        self._apply_number_settings()

        # P1-3: early-exit se nulla è cambiato e nessun trip/carica attivi
        _curr_inputs = (
            round(odometer, 2),
            round(battery, 1),
            charging,
            wb_state,
            location,
            self._wb_counter(),
            self._automation_sig(),
            keys["daily"],
        )
        if self._last_inputs == _curr_inputs and not self.trip.active and not self.charge_session and self.data:
            return self.data
        self._last_inputs = _curr_inputs

        sources_ok = any(
            hass.states.get(e) is not None
            for e in (
                o.get(CONF_ODOMETER),
                o.get(CONF_BATTERY_LEVEL),
                o.get(CONF_RANGE),
            )
            if e
        )

        # --- efficienza live ---------------------------------------------------
        avail_kwh = battery * self.capacity / 100.0
        if rng > 1 and avail_kwh > 0.5:
            eff_km_kwh = round(rng / avail_kwh, 2)
            eff_kwh_100 = round(100.0 * avail_kwh / rng, 2)
        else:
            eff_km_kwh = 0.0
            eff_kwh_100 = 0.0

        # --- contatori -----------------------------------------------------------
        for p in PERIODS:
            self.km_meters[p].tick(keys[p], odometer if odometer > 0 else None)
            self.wb_meters[p].tick(
                keys[p],
                self._wb_counter(),
                allow=wb_enabled and plug_ours and wb_state in WALLBOX_CHARGING_STATES,
                max_delta=30.0,
            )
            self.kwh_meters[p]["up"].tick(keys[p], avail_kwh, allow=True, max_delta=self.capacity * 0.35)
            self.kwh_meters[p]["down"].tick(keys[p], avail_kwh, allow=True, max_delta=self.capacity * 0.35)
        self.pct_daily["up"].tick(keys["daily"], battery if 0 <= battery <= 100 else None,
                                  allow=True, max_delta=25.0)
        self.pct_daily["down"].tick(keys["daily"], battery if 0 <= battery <= 100 else None,
                                    allow=True, max_delta=25.0)

        # --- temperatura esterna (opzionale) --------------------------------------
        temp_out = self._read_temp()

        # --- vampire drain: SoC persa da fermo (non carica, odometro fermo) --------
        fermo = (
            not charging
            and self._drain_odom_ref is not None
            and odometer <= self._drain_odom_ref + 0.05
        )
        if odometer > 0:
            self._drain_odom_ref = odometer
        self.drain_meter.tick(keys["daily"], battery if 0 <= battery <= 100 else None,
                              allow=fermo, max_delta=10.0)
        self.drain_mesi.tick(keys["monthly"], battery if 0 <= battery <= 100 else None,
                             allow=fermo, max_delta=10.0)

        # --- energia erogata in questo ciclo → accumula costi --------------------
        wb_delta = 0.0
        if wb_enabled:
            counter = self._wb_counter()
            charging_wb = wb_state in WALLBOX_CHARGING_STATES
            if counter is not None:
                if self._wb_counter_ref is not None:
                    d = counter - self._wb_counter_ref
                    if 0 < d <= 10:
                        wb_delta = d
                self._wb_counter_ref = counter
            if charging_wb and wb_delta > 0 and plug_ours:
                prezzo = self._price_for_zone(location or "home")
                aggiunta = wb_delta * prezzo
                for p in PERIODS:
                    m = self.cost_meters[p]
                    if m["key"] != keys[p]:
                        m["last"] = round(m["value"], 2)
                        m["key"] = keys[p]
                        m["value"] = 0.0
                    m["value"] += aggiunta
                self.cost_total += aggiunta

        # --- tempo sessione wallbox (contatore personale: parte oltre la soglia) --
        wb_sess_s = self._wb_sess_time
        if wb_enabled:
            soglia_w = self._setting_num("wb_start_w", DEFAULT_WB_START_W)
            if wb_power * 1000.0 > soglia_w:
                if self._wb_sess_start is None:
                    self._wb_sess_start = now.timestamp()
                wb_sess_s = now.timestamp() - self._wb_sess_start
                self._wb_sess_time = wb_sess_s
            else:
                self._wb_sess_start = None

        # --- viaggi --------------------------------------------------------------
        now_wall = now.timestamp()
        now_mono = __import__("time").monotonic()
        trip_opened = False
        closed_trip = None
        # coordinate GPS del tracker: servono a capire il movimento anche "fuori -> fuori"
        lat = lon = None
        _loc_ent = o.get(CONF_LOCATION_ENTITY)
        if _loc_ent:
            _st = hass.states.get(_loc_ent)
            if _st is not None:
                lat = _st.attributes.get("latitude")
                lon = _st.attributes.get("longitude")
        opened, _ = self.trip.tick(odometer, battery, location, eff_kwh_100, now_wall, now_mono, lat, lon)
        trip_opened = opened
        if self.trip.should_close(now_mono) or self.trip.arrived or (self.trip.active and (now_wall - self.trip.ts_start) > 6 * 3600):
            closed_trip = self.trip.close(location, eff_kwh_100, now_wall)
            if closed_trip is not None:
                self._enrich_trip(closed_trip)
                self.store.data["trips"].append(closed_trip)
                self._queue_geocode(closed_trip)

        # --- sessione di ricarica -------------------------------------------------
        finished_charge = None
        started_charge = False
        if charging:
            self._charge_off_polls = 0
            # DOPPIA VERIFICA: se si collega la carica il viaggio e' sicuramente finito
            if self.trip.active:
                chiuso_verifica = self.trip.close(location, eff_kwh_100, now_wall)
                if chiuso_verifica is not None:
                    self._enrich_trip(chiuso_verifica)
                    chiuso_verifica["verifica"] = "chiuso anticipato: auto collegata alla carica"
                    self.store.data["trips"].append(chiuso_verifica)
                    self._queue_geocode(chiuso_verifica)
                    closed_trip = chiuso_verifica
            if self.charge_session is None:
                self.charge_session = {
                    "id": int(time.time()),
                    "start_ts": time.time(),
                    "zone": location or "unknown",
                    "soc_start": battery,
                    "counter_start": self._wb_counter(),
                    "total_start": self._wb_total_counter(),
                    "kwh_accum": 0.0,
                    # delta wallbox passo-passo: supera i contatori che si azzerano
                    # o fanno salti a metà sessione (per questo 13 kWh → 4,67)
                    "wb_accum": 0.0,
                    # spina collegata al momento di avvio della sessione
                    "plug_ok": self._plug_connected(),
                    "ts_last": time.time(),
                    "power_max_kw": 0.0,
                    "odometro_inizio": odometer,
                    "prezzo": self._price_for_zone(location or "home"),
                }
                started_charge = True
            self.charge_session["soc_now"] = battery
            self.charge_session["power_kw"] = wb_power
            # la spina può scollegarsi a metà: il valore peggiore vince
            if self._plug_connected() is False:
                self.charge_session["plug_ok"] = False
            # picco di potenza della sessione: serve a distinguere AC (≤22 kW) da DC (fast)
            if wb_power > _f(self.charge_session.get("power_max_kw")):
                self.charge_session["power_max_kw"] = round(wb_power, 2)
            # energia wallbox accumulata a ogni ciclo (0 < delta ≤ 10 kWh per poll)
            if wb_delta > 0:
                self.charge_session["wb_accum"] = round(
                    _f(self.charge_session.get("wb_accum")) + wb_delta, 4)
            # integrale della potenza istantanea: conta i kWh se i contatori wallbox mancano
            _now_ts = time.time()
            _dt_h = max(_now_ts - _f(self.charge_session.get("ts_last"), _now_ts), 0.0) / 3600.0
            self.charge_session["kwh_accum"] = round(
                _f(self.charge_session.get("kwh_accum")) + wb_power * _dt_h, 4)
            self.charge_session["ts_last"] = _now_ts
            if (time.time() - self.charge_session["start_ts"]) > 26 * 3600:
                finished_charge = self._finalize_charge(location, battery)
        elif self.charge_session is not None:
            self._charge_off_polls += 1
            if self._charge_off_polls >= 2:
                finished_charge = self._finalize_charge(location, battery)

        # --- storico giornaliero ---------------------------------------------------
        history = self.store.data["daily"]
        today_key = keys["daily"]
        # --- base odometro all'installazione: serve al confronto "km da quando usi l'integrazione"
        if odometer and odometer > 0:
            _inst = self.store.data.setdefault("install", {})
            _man = _f(self.opts.get(CONF_INSTALL_ODO), 0.0)
            if _man > 0:
                # baseline scelta a mano in Configura: vale piu' della cattura automatica
                if _inst.get("odometer") != _man:
                    _inst["odometer"] = _man
                    _inst["date"] = _inst.get("date") or today_key
            elif not _inst.get("odometer"):
                _inst["odometer"] = round(odometer, 1)
                _inst["date"] = today_key
        if not self.today_rec or self.today_rec.get("data") != today_key:
            if self.today_rec.get("data"):
                prev = dict(self.today_rec)
                km_prev = _f(prev.get("km"))
                if km_prev >= 0.5:
                    prev["eff"] = round(_f(prev.get("kwh")) / km_prev * 100, 2) if km_prev else 0.0
                    history.append(prev)
                history.sort(key=lambda d: d.get("data", ""))
                del history[:-365]
            self.today_rec = {"data": today_key, "km": 0.0, "kwh": 0.0, "pct": 0.0, "eff": 0.0,
                              "soc_start": None}
        # riferimento reale (SoC dall'app Renault): massimo della giornata NON in carica.
        # Il massimo evita che un riavvio di HA a metà giornata sposti la baseline per errore.
        if not charging:
            _soc_rif = round(_f(battery), 1)
            if self.today_rec.get("soc_start") is None or _soc_rif > self.today_rec["soc_start"]:
                self.today_rec["soc_start"] = _soc_rif
        km_oggi = _f(self.km_meters["daily"].value)
        kwh_oggi = _f(self.kwh_meters["daily"]["down"].value)
        self.today_rec.update({
            "km": round(km_oggi, 1),
            "kwh": round(kwh_oggi, 2),
            "pct": round(_f(self.pct_daily["down"].value), 1),
            "drain": round(_f(self.drain_meter.value), 1),
            "temp": round(temp_out, 1) if temp_out is not None else None,
        })
        self.today_rec["eff"] = (
            round(kwh_oggi / km_oggi * 100, 2) if km_oggi > 0.5 else 0.0
        )

        # --- archivio mensile permanente: km del mese aggiornati live,
        #     congelati al cambio mese (cosi lo storico anni funziona per sempre)
        arch_mese = self.store.data.setdefault("monthly_km", {})
        mese_key_now = today_key[:7]
        arch_mese[mese_key_now] = round(_f(self.km_meters["monthly"].value), 1)
        prev_mese = (now - timedelta(days=1)).strftime("%Y-%m")
        if prev_mese != mese_key_now and prev_mese not in arch_mese:
            # primo tick dopo il cambio mese: congela il mese appena chiuso
            arch_mese[prev_mese] = round(_f(self.km_meters["monthly"].last), 1)

        self.persist()

        # --- stime ricarica ---------------------------------------------------------
        # target: se la carica programmata è attiva uso il SUO SoC (quello dell'automazione),
        # altrimenti l'obiettivo generale. Prima erano due valori diversi e la stima sbagliava.
        target = self.target_soc
        _sc_prog = (self.store.data.get("schedule", {}) or {}).get("ricarica") or {}
        if _sc_prog.get("attivo") and _sc_prog.get("soc"):
            target = _f(_sc_prog.get("soc"), target)
        needed_pct = max(target - battery, 0.0)
        needed_kwh = needed_pct * self.capacity / 100.0
        minutes_left = 0
        if not charging:
            est_status = "Completo" if needed_pct <= 0 else "Non in carica"
            completion = "--:--" if needed_pct > 0 else "Completo"
            tempo_hms = "00:00:00"
        elif needed_pct <= 0:
            est_status = "Completo"
            completion = "Completo"
            tempo_hms = "00:00:00"
        elif wb_power > 0.2:
            est_status = "In carica"
            adjusted = wb_power * self.charging_eff
            if adjusted > 0:
                minutes_left = int(needed_kwh / adjusted * 60)
                end_dt = now + timedelta(minutes=minutes_left)
                completion = end_dt.strftime("%H:%M")
                hh, mm = divmod(minutes_left, 60)
                tempo_hms = "{:02d}:{:02d}:00".format(hh, mm)
            else:
                est_status = "In carica (potenza non nota)"
                completion = "--:--"
                tempo_hms = "Non disponibile"
        else:
            est_status = "In carica (potenza non nota)"
            completion = "--:--"
            tempo_hms = "Non disponibile"

        current_price = self._price_for_zone(location or "home")
        costo_stimato = round(needed_kwh * current_price, 2)

        # --- tipo ricarica ------------------------------------------------------------
        if not charging:
            tipo_ricarica = "Non in Carica"
        elif (location or "") == "home":
            tipo_ricarica = "Ricarica a Casa"
        elif self.solar_zone and location == self.solar_zone:
            tipo_ricarica = "Ricarica Fotovoltaico"
        else:
            tipo_ricarica = "Ricarica Pubblica"

        # --- viaggi/ricariche aggregate (offload su executor) --------------------------
        trips = list(self.store.data["trips"])
        charges = list(self.store.data["charges"])
        heavy = await self.hass.async_add_executor_job(
            lambda: self._compute_heavy(trips, charges, list(self.store.data["daily"]), today_key, keys, now)
        )
        t7 = heavy["t7"]; t30 = heavy["t30"]; t90 = heavy["t90"]
        trips_oggi_list = heavy["trips_oggi_list"]
        charges_oggi = heavy["charges_oggi"]; charges_mese = heavy["charges_mese"]
        ultimo_trip = trips[-1] if trips else None
        mese_key = keys["monthly"]

        # --- risparmio vs termica ----------------------------------------------------------------
        # Confronto "auto termica" vs "auto elettrica": quello che AVRESTI speso a benzina/diesel
        # (carburante + tagliandi + bollo) contro quello che HAI speso (ricariche + tagliandi + bollo EV).
        savings: dict[str, Any] = {}
        if self.fuel_enabled:
            litri_100 = self.fuel_consumption
            prezzo_l = self._prezzo_termico()
            km_tot = odometer

            def _chg_cost(pred) -> float:
                """Costo ricariche del periodo, dai RECORD (i meter live non sono affidabili)."""
                return round(sum(_f(c.get("costo")) for c in charges
                                 if pred(str(c.get("data", "")))), 2)

            def _km_of(pred) -> float:
                """Km del periodo: prima il meter, altrimenti somma dei viaggi."""
                v = 0.0
                for t in trips:
                    if pred(str(t.get("data", ""))):
                        v += _f(t.get("km"))
                return v

            def _periodo(label: str, pred, km_meter: float) -> None:
                km = km_meter if km_meter > 0 else _km_of(pred)
                termica = km * litri_100 * prezzo_l / 100.0
                elettrico = _chg_cost(pred)
                savings[label] = round(termica - elettrico, 2)
                if label == "totale":
                    savings["termica_totale"] = round(termica, 2)
                    savings["elettrico_totale"] = elettrico

            _periodo("totale", lambda d: True, km_tot)
            _periodo("mese", lambda d: d[:7] == keys["monthly"],
                     _f(self.km_meters["monthly"].value))
            _periodo("anno", lambda d: d[:4] == keys["yearly"],
                     _f(self.km_meters["yearly"].value))
            savings["prezzo_termico"] = prezzo_l
            savings["km_totali"] = round(km_tot, 1)

            # --- dettaglio per voce: termica vs elettrica --------------------------
            carb_termica = _f(savings.get("termica_totale"))
            carb_ev = _f(savings.get("elettrico_totale"))
            tag_termica = tag_ev = bollo_termica = bollo_ev = 0.0
            if self.maint_enabled:
                anni = max(km_tot / 15000.0, 0.1)
                tagliandi_termici = int(km_tot // self.tagliando_intervallo)
                tag_termica = tagliandi_termici * self.tag_termico
                tag_ev = round(
                    sum(_f(m.get("costo")) for m in self.store.data.get("maintenance", [])), 2)
                bollo_termica = anni * self.bollo_termico
                bollo_ev = anni * self.bollo_ev
                savings["tagliandi"] = round(tag_termica - tag_ev, 2)
                savings["tagliandi_teoria"] = round(tag_termica, 2)
                savings["tagliandi_reale"] = tag_ev
                savings["tagliandi_n"] = tagliandi_termici
                savings["bollo"] = round(bollo_termica - bollo_ev, 2)

            # --- ricariche fatte PRIMA dell'installazione (dichiarate dall'utente) -----
            # Senza, il risparmio sarebbe falsato: i km totali (odometro) contano tutti,
            # ma le ricariche registrate solo da quando usi l'integrazione.
            pre_kwh = _f(self.opts.get(CONF_PRE_KWH), 0.0)
            pre_eur = _f(self.opts.get(CONF_PRE_EUR), 0.0)
            if pre_eur <= 0 and pre_kwh > 0:
                pre_eur = pre_kwh * self.price_home
            ric_reg = carb_ev  # ricariche registrate dall'integrazione
            savings["pre_kwh"] = round(pre_kwh, 2)
            savings["pre_eur"] = round(pre_eur, 2)
            # il valore DICHIARATO entra anche nei totali "ufficiali" (sensore Risparmio Totale,
            # risp_tot del pannello): altrimenti i due numeri non coincidono col box di confronto
            savings["elettrico_totale"] = round(ric_reg + pre_eur, 2)
            savings["totale"] = round(_f(savings.get("termica_totale"))
                                      - savings["elettrico_totale"], 2)

            savings["termica"] = {"carburante": round(carb_termica, 2),
                                  "tagliandi": round(tag_termica, 2),
                                  "bollo": round(bollo_termica, 2),
                                  "totale": round(carb_termica + tag_termica + bollo_termica, 2)}
            savings["elettrica"] = {"ricariche": round(ric_reg, 2),
                                    "ricariche_pre": round(pre_eur, 2),
                                    "tagliandi": round(tag_ev, 2),
                                    "bollo": round(bollo_ev, 2),
                                    "totale": round(ric_reg + pre_eur + tag_ev + bollo_ev, 2)}
            savings["differenza"] = round(savings["termica"]["totale"]
                                          - savings["elettrica"]["totale"], 2)
            savings["netto"] = savings["differenza"]

            # --- confronto "da installazione": km reali dal primo avvio, senza stime --------
            # È il numero PIÙ AFFIDABILE: entrambi i lati nascono da dati reali
            # (km percorsi con l'integrazione attiva vs ricariche registrate), zero input manuale.
            _inst = self.store.data.get("install", {})
            _odo_base = _f(_inst.get("odometer"))
            savings["install_odometer"] = round(_odo_base, 1) if _odo_base > 0 else None
            savings["install_date"] = _inst.get("date") or None
            if _odo_base > 0 and odometer > _odo_base:
                km_i = odometer - _odo_base
                termica_i = km_i * litri_100 * prezzo_l / 100.0
                elettrica_i = _f(savings.get("elettrico_totale"))  # solo ricariche registrate
                savings["da_installazione"] = {
                    "km": round(km_i, 1),
                    "termica": round(termica_i, 2),
                    "elettrica": round(elettrica_i, 2),
                    "differenza": round(termica_i - elettrica_i, 2),
                }

            # --- fotovoltaico: quanto hai risparmiato caricando col sole -----------
            kwh_fv = sum(_f(c.get("kwh")) for c in charges if c.get("tipo") == "Fotovoltaico")
            kwh_casa = sum(_f(c.get("kwh")) for c in charges if c.get("tipo") == "Casa")
            kwh_pub = sum(_f(c.get("kwh")) for c in charges if c.get("tipo") == "Pubblica")
            savings["fv_kwh"] = round(kwh_fv, 2)
            # il kWh da FV costa il prezzo FV (spesso 0): risparmio = differenza vs rete casa
            risparmio_kwh = max(self.price_home - self.price_solar, 0.0)
            savings["fv_eur"] = round(kwh_fv * risparmio_kwh, 2)
            savings["casa_kwh"] = round(kwh_casa, 2)
            savings["pubblica_kwh"] = round(kwh_pub, 2)

        stats_all = heavy["stats_all"]
        best_eff = heavy["best_eff"]

        # --- tagliandi --------------------------------------------------------------------------
        manutenzioni = self.store.data.get("maintenance", [])
        costo_tagliandi = round(sum(_f(m.get("costo")) for m in manutenzioni), 2)
        ultimo_tag_km = max((_f(m.get("km")) for m in manutenzioni), default=0.0)
        prossimo_tag_km = ultimo_tag_km + self.tagliando_intervallo if ultimo_tag_km else self.tagliando_intervallo

        # kWh per 1% di batteria (con SOH ufficiale)
        soh_u = max(self._setting_num("soh_official", 100.0), 40.0)
        kwh_per_1pct = round(self.capacity * (soh_u / 100.0) / 100.0, 3)

        # --- CO2 risparmiata ---------------------------------------------------------
        co2: dict[str, Any] = {}
        if self.co2_enabled:
            anno_key = keys["yearly"]
            kwh_caricati_tot = sum(_f(c.get("kwh")) for c in charges)
            kwh_caricati_anno = sum(
                _f(c.get("kwh")) for c in charges if str(c.get("data", ""))[:4] == str(now.year)
            )
            co2_termica = odometer * self.co2_thermal_gkm / 1000.0
            co2_ev = kwh_caricati_tot * self.co2_grid_gkwh / 1000.0
            km_anno = sum(
                _f(t.get("km")) for t in trips if str(t.get("data", ""))[:4] == str(now.year)
            )
            co2 = {
                "totale": round(co2_termica - co2_ev, 1),
                "termica": round(co2_termica, 1),
                "ev": round(co2_ev, 1),
                "anno": round(
                    km_anno * self.co2_thermal_gkm / 1000.0
                    - kwh_caricati_anno * self.co2_grid_gkwh / 1000.0, 1
                ),
            }

        # --- scadenze (dinamiche da store: assicurazione/bollo/revisione/tagliando) ------------
        scadenze: list[dict[str, Any]] = []
        if self.scadenze_enabled or self.maint_enabled:
            from datetime import date as _date
            oggi_d = now.date()
            scad_cfg = self.store.data.setdefault("scadenze", {})
            coppie = [
                ("Assicurazione", scad_cfg.get("assicurazione") or self.scad_assicurazione),
                ("Bollo", scad_cfg.get("bollo") or self.scad_bollo),
                ("Revisione", scad_cfg.get("revisione") or self.scad_revisione),
            ]
            for label, raw in coppie:
                raw = str(raw or "").strip()
                if not raw:
                    continue
                prossima = None
                try:
                    d0 = _date.fromisoformat(raw)
                    prossima = _date(oggi_d.year, d0.month, d0.day)
                except ValueError:
                    pass
                if prossima is None:
                    try:
                        parts = raw.split("-")
                        if len(parts) == 2:
                            prossima = _date(oggi_d.year, int(parts[0]), int(parts[1]))
                    except (ValueError, TypeError):
                        continue
                if prossima is None:
                    continue
                if prossima < oggi_d:
                    try:
                        prossima = _date(oggi_d.year + 1, prossima.month, prossima.day)
                    except ValueError:
                        continue
                scadenze.append({"nome": label, "data": prossima.isoformat(),
                                 "giorni": (prossima - oggi_d).days})

            # tagliando / cambio gomme: scadenza per km e/o data
            km_anno = max(_f(self.km_meters["yearly"].value), 1.0)
            km_giorno = km_anno / 365.0
            manutenzioni = self.store.data.get("maintenance", [])

            def _due(label: str, key: str, interval_km: float, last_change: bool = False) -> None:
                """Calcola la scadenza per km (+ eventuale data).

                `last_change=True` (gomme): il valore salvato è il km dell'**ultimo cambio**,
                quindi l'obiettivo è `ultimo + intervallo`.
                `last_change=False` (tagliando): il valore salvato è già l'obiettivo in km.
                """
                recs = [m for m in manutenzioni if key in str(m.get("tipo", "")).lower()]
                last = max(recs, key=lambda m: (str(m.get("data", "")), m.get("id", 0)), default=None)
                last_km = _f(last.get("km")) if last else 0.0
                kmv = scad_cfg.get(f"{key}_km")
                if kmv is None:
                    base = last_km if last_km > 0 else (odometer if odometer > 0 else 0.0)
                    kmv = base + interval_km
                elif last_change:
                    # ultimo cambio dichiarato → obiettivo = ultimo + intervallo
                    kmv = _f(kmv) + interval_km
                if kmv:
                    target = _f(kmv)
                    mancanti = target - odometer
                    scadenze.append({"nome": label, "km": round(mancanti, 0),
                                     "data": f"a {target:.0f} km",
                                     "giorni": max(int(mancanti / km_giorno), 0)})
                dv = str(scad_cfg.get(f"{key}_data") or "").strip()
                if dv:
                    try:
                        td = _date.fromisoformat(dv)
                        scadenze.append({"nome": label, "data": td.isoformat(),
                                         "giorni": max((td - oggi_d).days, 0)})
                    except ValueError:
                        pass

            _due("Tagliando", "tagliando", self.tagliando_intervallo)
            # gomme: il valore impostato è l'ULTIMO CAMBIO → obiettivo = ultimo + intervallo
            _due("Cambio gomme", "gomme", self.tyre_interval, last_change=True)
            # tagliando annuale conteggiato dalla data di consegna dell'auto
            if self.purchase_date:
                try:
                    pd = _date.fromisoformat(str(self.purchase_date)[:10])
                    anniv = pd.replace(year=pd.year + (oggi_d.year - pd.year))
                    if anniv < oggi_d:
                        anniv = pd.replace(year=pd.year + (oggi_d.year - pd.year) + 1)
                    scadenze.append({"nome": "Tagliando annuale (consegna)", "data": anniv.isoformat(),
                                     "giorni": (anniv - oggi_d).days})
                except ValueError:
                    pass
            # se ci sono ENTRAMBI i tagliandi (km e consegna) tengo solo quello della consegna:
            # erano due voci per la stessa cosa e la prima restava a 0 giorni
            ha_km = any(s["nome"] == "Tagliando" for s in scadenze)
            ha_consegna = any(str(s["nome"]).startswith("Tagliando annuale") for s in scadenze)
            if ha_km and ha_consegna:
                scadenze = [s for s in scadenze if s["nome"] != "Tagliando"]
            scadenze.sort(key=lambda s: s["giorni"])
            await self._check_notifications(scadenze, now)

        zone_routes = heavy["zone_routes"]
        zone_best = heavy["zone_best"]
        zone_worst = heavy["zone_worst"]
        best_trip = heavy["best_trip"]
        worst_trip = heavy["worst_trip"]

        # energia caricata a casa (per Energy Dashboard)
        energia_casa_tot = round(
            sum(_f(c.get("kwh")) for c in charges if c.get("tipo") == "Casa"), 2
        )
        # energia caricata dal fotovoltaico (per Energy Dashboard: fonte solare)
        energia_fv_tot = round(
            sum(_f(c.get("kwh")) for c in charges if c.get("tipo") == "Fotovoltaico"), 2
        )

        # energia caricata differenziata per tipo (totale) + FV del mese
        by_type: dict[str, float] = {"Casa": 0.0, "Fotovoltaico": 0.0, "Pubblica": 0.0}
        for c in charges:
            t = str(c.get("tipo", ""))
            if t in by_type:
                by_type[t] = round(by_type[t] + _f(c.get("kwh")), 2)
        fv_mese = round(sum(
            _f(c.get("kwh")) for c in charges
            if c.get("tipo") == "Fotovoltaico" and str(c.get("data", ""))[:7] == keys["monthly"]
        ), 2)

        def _week_key(d: str) -> str:
            try:
                iso = datetime.strptime(d, "%Y-%m-%d").isocalendar()
                return "%s-W%02d" % (iso[0], iso[1])
            except (ValueError, TypeError):
                return ""

        yday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        def _trips_sum(pred) -> tuple[float, float, float]:
            km = pct = 0.0
            for t in trips:
                if pred(str(t.get("data", ""))):
                    km += _f(t.get("km"))
                    pct += abs(_f(t.get("batteria_delta")))
            # kWh consumati dal SoC REALE (delta % × capacità EFFETTIVA con SOH): è il
            # consumo effettivo; il calcolo dai km sbaglia sui tragitti corti.
            kwh = round(pct / 100.0 * self._eff_capacity(), 2)
            return round(km, 0), kwh, round(pct, 1)

        o_km, o_kwh, o_pct = _trips_sum(lambda d: d == today_key)
        i_km, i_kwh, i_pct = _trips_sum(lambda d: d == yday)
        w_km, w_kwh, _ = _trips_sum(lambda d: _week_key(d) == keys["weekly"])
        m_km, m_kwh, _ = _trips_sum(lambda d: d[:7] == keys["monthly"])
        y_km, y_kwh, _ = _trips_sum(lambda d: d[:4] == keys["yearly"])

        def _pct_from_kwh(kwh: float) -> float:
            cap = self.capacity or 60.0
            return round(kwh / cap * 100.0, 1) if kwh > 0 else 0.0

        def _pct(trip_pct: float, kwh: float) -> float:
            # priorità al delta batteria reale dei viaggi, altrimenti kWh/capacità
            return trip_pct if trip_pct > 0 else _pct_from_kwh(kwh)

        # --- ricariche per periodo, derivate dai RECORD (fonte di verità) ----------
        # I meter live dipendono dallo stato wallbox "charging" nel polling: se salta,
        # costi ed energia restavano a 0. Qui si somma direttamente l'archivio ricariche.
        def _chg_date(c: dict) -> str:
            """Data 'effettiva' della ricarica per i totali di periodo.

            Se la ricarica attraversa la mezzanotte (es. 23:06 → 00:12) conta il giorno di FINE:
            l'energia è consegnata alla fine, così «oggi» la include.
            """
            d = str(c.get("data", ""))
            oi, of = str(c.get("ora_inizio", "")), str(c.get("ora_fine", ""))
            if d and oi and of and of < oi:
                try:
                    return (datetime.strptime(d, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                except ValueError:
                    return d
            return d

        def _chg_sum(pred) -> tuple[float, float]:
            kwh = costo = 0.0
            for c in charges:
                if pred(_chg_date(c)):
                    kwh += _f(c.get("kwh"))
                    costo += _f(c.get("costo"))
            return round(kwh, 2), round(costo, 2)

        def _prev_week_key() -> str:
            iso = (now.date() - timedelta(days=7)).isocalendar()
            return "%s-W%02d" % (iso[0], iso[1])

        _pk = keys["monthly"]
        _prev_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        _prev_year = str(now.year - 1)

        chg = {
            "daily": _chg_sum(lambda d: d == today_key),
            "yday": _chg_sum(lambda d: d == yday),
            "weekly": _chg_sum(lambda d: _week_key(d) == keys["weekly"]),
            "prev_week": _chg_sum(lambda d: _week_key(d) == _prev_week_key()),
            "monthly": _chg_sum(lambda d: d[:7] == _pk),
            "prev_month": _chg_sum(lambda d: d[:7] == _prev_month),
            "yearly": _chg_sum(lambda d: d[:4] == keys["yearly"]),
            "prev_year": _chg_sum(lambda d: d[:4] == _prev_year),
        }
        _prev_key = {"daily": "yday", "weekly": "prev_week",
                     "monthly": "prev_month", "yearly": "prev_year"}

        def _prev_of(p: str) -> tuple[float, float]:
            return chg[_prev_key[p]]

        # --- statistiche complessive ricariche (AC/DC, Casa/Pubblica) --------------
        cstats: dict[str, Any] = {
            "n": 0, "kwh": 0.0, "costo": 0.0, "durata_min": 0, "picco_kw": 0.0,
            "ac": {"n": 0, "kwh": 0.0}, "dc": {"n": 0, "kwh": 0.0},
            "casa": {"n": 0, "kwh": 0.0}, "pubblica": {"n": 0, "kwh": 0.0},
        }
        for c in charges:
            kwh_c = _f(c.get("kwh"))
            cstats["n"] += 1
            cstats["kwh"] += kwh_c
            cstats["costo"] += _f(c.get("costo"))
            cstats["durata_min"] += int(_f(c.get("durata_min")))
            cstats["picco_kw"] = max(cstats["picco_kw"],
                                     _f(c.get("potenza_max_kw")), _f(c.get("potenza_media_kw")))
            ad = c.get("ac_dc") or _ac_dc_from_power(
                c.get("potenza_max_kw"), c.get("potenza_media_kw"))
            grp = "dc" if ad == "DC" else "ac"
            cstats[grp]["n"] += 1
            cstats[grp]["kwh"] += kwh_c
            casa = str(c.get("tipo", "")) != "Pubblica"
            cstats["casa" if casa else "pubblica"]["n"] += 1
            cstats["casa" if casa else "pubblica"]["kwh"] += kwh_c
        for grp in ("ac", "dc", "casa", "pubblica"):
            cstats[grp]["kwh"] = round(cstats[grp]["kwh"], 2)
        cstats["kwh"] = round(cstats["kwh"], 2)
        cstats["costo"] = round(cstats["costo"], 2)
        cstats["picco_kw"] = round(cstats["picco_kw"], 2)
        cstats["prezzo_medio"] = round(cstats["costo"] / cstats["kwh"], 3) if cstats["kwh"] > 0 else 0.0
        cstats["durata_media_min"] = round(cstats["durata_min"] / cstats["n"], 0) if cstats["n"] else 0.0

        # --- consumi vs temperatura esterna (grafico a dispersione) ----------------
        # un punto per viaggio >= 3 km, con la temperatura esterna registrata all'arrivo
        consumi_temp = [
            {"d": str(t.get("data", "")),
             "t": round(_f(t.get("temp_est")), 1),
             "e": round(_f(t.get("kwh_per_100km")), 2)}
            for t in trips
            if _f(t.get("km")) >= 3 and _f(t.get("kwh_per_100km")) > 0
            and t.get("temp_est") is not None
        ][-500:]

        percorrenza = [
            {"nome": "Oggi", "pct": _pct(o_pct, o_kwh), "usati": o_kwh,
             "caricati": chg["daily"][0], "km": o_km},
            {"nome": "Ieri", "pct": _pct(i_pct, i_kwh), "usati": i_kwh,
             "caricati": chg["yday"][0], "km": i_km},
            {"nome": "Settimana", "usati": w_kwh,
             "caricati": chg["weekly"][0], "km": w_km},
            {"nome": "Settimana prec.", "usati": 0.0,
             "caricati": chg["prev_week"][0], "km": 0.0},
            {"nome": "Mese", "usati": m_kwh,
             "caricati": chg["monthly"][0], "km": m_km},
            {"nome": "Mese prec.", "usati": 0.0,
             "caricati": chg["prev_month"][0], "km": 0.0},
            {"nome": "Anno", "usati": y_kwh,
             "caricati": chg["yearly"][0], "km": y_km},
            {"nome": "Anno prec.", "usati": 0.0,
             "caricati": chg["prev_year"][0], "km": 0.0},
        ]

        # --- storico mensile multi-anno (costo, ricaricati kWh, km) ---------------
        mesi: dict[str, dict[str, dict[str, float]]] = {}
        for c in charges:
            d = str(c.get("data", ""))
            if len(d) >= 7:
                row = mesi.setdefault(d[:4], {}).setdefault(d[5:7], {"costo": 0.0, "kwh": 0.0, "km": 0.0})
                row["costo"] += _f(c.get("costo"))
                row["kwh"] += _f(c.get("kwh"))
        for t in trips:
            d = str(t.get("data", ""))
            if len(d) >= 7:
                row = mesi.setdefault(d[:4], {}).setdefault(d[5:7], {"costo": 0.0, "kwh": 0.0, "km": 0.0})
                row["km"] += _f(t.get("km"))
        for ym, km in self.store.data.get("monthly_km", {}).items():
            ym = str(ym)
            if len(ym) >= 7:
                row = mesi.setdefault(ym[:4], {}).setdefault(ym[5:7], {"costo": 0.0, "kwh": 0.0, "km": 0.0})
                row["km"] = max(row["km"], _f(km))
        mesi_storico = {
            y: {m: {k: round(v, 2) for k, v in row.items()} for m, row in mm.items()}
            for y, mm in mesi.items()
        }

        charges_filtered = self._filter_charges(charges, now)
        report = self._build_report(now, keys, today_key)

        data: dict[str, Any] = {
            "available": sources_ok,
            "odometer": round(odometer, 1),
            "battery": round(battery, 1),
            "soc_start_oggi": self.today_rec.get("soc_start"),
            "range": round(rng, 1),
            "charging": charging,
            "charging_state": charging_raw,
            "plug": plug,
            "location": location,
            "capacity": self.capacity,
            "target_soc": target,
            "battery_kwh": round(avail_kwh, 2),
            "eff_km_per_kwh": eff_km_kwh,
            "eff_kwh_100km": eff_kwh_100,
            "km": {p: self.km_meters[p].to_dict() for p in PERIODS},
            # energia/costo per periodo dai RECORD: i meter live restano come "last"
            "wb_energy": {p: {"value": chg[p][0], "last": _prev_of(p)[0]} for p in PERIODS},
            "cost": {p: {"value": chg[p][1], "last": _prev_of(p)[1]} for p in PERIODS},
            "cost_total": round(self.cost_total, 2),
            "pct_daily": {k: v.to_dict() for k, v in self.pct_daily.items()},
            "kwh_batt": {
                p: {d: self.kwh_meters[p][d].to_dict() for d in ("up", "down")}
                for p in PERIODS
            },
            "wb_power_kw": round(wb_power, 2),
            "wb_session_time": int(wb_sess_s),
            "wb_session_active": self._wb_sess_start is not None,
            "wb_state": wb_state,
            "tipo_ricarica": tipo_ricarica,
            "estimate": {
                "status": est_status,
                "tempo": tempo_hms,
                "minuti": minutes_left,
                "completion": completion,
                "kwh_needed": round(needed_kwh, 2),
                "costo_stimato": costo_stimato,
            },
            "trip": {
                "active": self.trip.active,
                "km": round(max(self.trip.mileage_now - self.trip.mileage_start, 0), 1),
                "battery_delta": round(max(self.trip.battery_start - self.trip.battery_now, 0), 1),
                "durata_min": int((time.time() - self.trip.ts_start) / 60) if self.trip.active else 0,
                "zona_partenza": self.trip.zone_start,
                "ts_inizio": datetime.fromtimestamp(self.trip.ts_start, self.trip.tz).isoformat()
                if self.trip.active
                else "",
            },
            "last_trip": ultimo_trip,
            "trips_recent": sorted(t30, key=lambda t: (t.get("data"), t.get("ora_inizio")), reverse=True)[:60],
            "stats_all": stats_all,
            "best_eff": best_eff,
            "kwh_per_1pct": kwh_per_1pct,
            "maintenance": {
                "items": manutenzioni[-50:],
                "n": len(manutenzioni),
                "costo_totale": costo_tagliandi,
                "ultimo_km": ultimo_tag_km,
                "prossimo_km": prossimo_tag_km,
                "intervallo": self.tagliando_intervallo,
            },
            "stats_7d": aggregate(t7),
            "stats_30d": aggregate(t30),
            "stats_90d": aggregate(t90),
            "days_grouped": group_by_day(sorted(t30, key=lambda t: t.get("data")))[-31:],
            "history_days": _merge_history(history, group_by_day(sorted(t30, key=lambda t: t.get("data")))[-31:]),
            "trips_oggi": len(trips_oggi_list),
            "km_oggi_trip": round(sum(_f(t.get("km")) for t in trips_oggi_list), 1),
            "charges_oggi": len(charges_oggi),
            "charges_mese": len(charges_mese),
            "last_charge": charges[-1] if charges else None,
            "savings": savings,
            "health": dict(self.store.data.get("health", {})),
            "mesi_storico": mesi_storico,
            "charges_filtered": charges_filtered,
            "charges_stats": cstats,
            "consumi_temp": consumi_temp,
            "schedule": dict(self.store.data.get("schedule", {})),
            "gse": self._gse_info(),
            "report": report,
            "temp_out": temp_out,
            "drain_oggi_pct": round(self.drain_meter.value, 1),
            "drain_oggi_kwh": round(self.drain_meter.value * kwh_per_1pct, 2),
            "drain_mese_pct": round(self.drain_mesi.value, 1),
            "drain_mese_kwh": round(self.drain_mesi.value * kwh_per_1pct, 2),
            "co2": co2,
            "scadenze": scadenze,
            "zone_routes": zone_routes,
            "zone_best": zone_best,
            "zone_worst": zone_worst,
            "best_trip": best_trip,
            "worst_trip": worst_trip,
            "energia_casa_totale": energia_casa_tot,
            "energia_fv_totale": energia_fv_tot,
            "charges_by_type": by_type,
            "fv_mese": fv_mese,
            "percorrenza": percorrenza,
            "assicurazione": {
                "data": self.store.data.get("scadenze", {}).get("assicurazione", ""),
                "costo": self.assicurazione_costo,
            },
            "events": {
                "trip_opened": trip_opened,
                "trip_closed": closed_trip,
                "charge_started": started_charge,
                "charge_finished": finished_charge,
            },
        }
        self._maybe_backfill_geocode()
        await self._handle_charge_events(data["events"], data, now)
        await self._balance_solar(data, wb_state)
        await self._home_balance(wb_state)
        await self._apply_gse(wb_state, bool(data.get("charging")))
        data["balance"] = dict(self.store.data.get("counters", {}).get("balance_last", {}))
        data["home_balance"] = dict(self._home_last)
        # cronologia posizione (timeline nel pannello): registra i cambi di zona
        _loc = str(data.get("location") or "")
        if _loc and _loc != self._last_pos_loc:
            hist = self.store.data.setdefault("pos_history", [])
            hist.append({"ts": datetime.now().isoformat(timespec="seconds"),
                         "loc": self._zone_label(_loc)})
            del hist[:-200]
            self._last_pos_loc = _loc
            self.persist(force=True)
        data["pos_history"] = list(self.store.data.get("pos_history", []))
        # stato on/off automazioni: seed una volta (dopo il caricamento), poi IMPONI la scelta
        if not self._auto_restored and self._managed_auto_ids():
            self.save_auto_states()
            self._auto_restored = True
        if self._auto_restored:
            try:
                await self.async_restore_auto_states()
            except Exception:  # noqa: BLE001
                pass
        return data

    # ------------------------------------------------------------ fine ricarica
    def _finalize_charge(self, zone: str, battery: float) -> dict[str, Any]:
        s = self.charge_session
        assert s is not None
        durata_min = int((time.time() - s["start_ts"]) / 60)
        counter_end = self._wb_counter()
        total_end = self._wb_total_counter()
        z = (s.get("zone") or zone or "unknown").lower()
        if z == "home":
            tipo = "Casa"
        elif self.solar_zone and z == self.solar_zone:
            tipo = "Fotovoltaico"
        else:
            tipo = "Pubblica"
        # Spina scollegata a metà sessione → la wallbox stava erogando verso un'altra
        # auto: l'energia misurata NON è della nostra Renault, si ricade sul delta SoC.
        if s.get("plug_ok") is False:
            measured = 0.0
            accum = 0.0
        else:
            measured = _best_measured_delta((
                (s.get("counter_start"), counter_end),
                (s.get("total_start"), total_end),
            ))
            # i contatori fanno salti (reset, sessioni altrui): il delta passo-passo
            # della sessione è la misura più affidabile, si prende il migliore
            accum = max(_f(s.get("kwh_accum")), _f(s.get("wb_accum")))
        kwh, origine = _charge_energy(
            measured, accum, tipo, s.get("soc_start"), battery, self.capacity,
        )
        if origine == "casa_senza_misura":
            _LOGGER.warning(
                "Ricarica a casa senza misura wallbox: energia stimata dal SoC "
                "(mappa i contatori in Configura → Wallbox)"
            )
        costo = round(kwh * _f(s.get("prezzo"), self._price_for_zone(z)), 2)
        ts_start = datetime.fromtimestamp(s["start_ts"])
        record = {
            "id": s["id"],
            "data": ts_start.strftime("%Y-%m-%d"),
            "ora_inizio": ts_start.strftime("%H:%M"),
            "ora_fine": datetime.now().strftime("%H:%M"),
            "durata_min": durata_min,
            "kwh": round(kwh, 2),
            "soc_start": round(_f(s.get("soc_start")), 1),
            "soc_end": round(battery, 1),
            "potenza_media_kw": round(kwh / (durata_min / 60.0), 2) if durata_min > 5 else 0.0,
            "potenza_max_kw": round(_f(s.get("power_max_kw")), 2),
            "ac_dc": _ac_dc_from_power(_f(s.get("power_max_kw")),
                                       kwh / (durata_min / 60.0) if durata_min > 5 else 0.0),
            "costo": costo,
            "tipo": tipo,
            # posizione della ricarica (per la notifica di fine carica)
            "zona": self._zone_label(str(s.get("zone") or zone or "")),
        }
        if origine is not None:
            record["stima"] = origine

        # --- salute batteria (solo ricariche a casa misurate dalla wallbox) -------
        delta_pct = battery - _f(s.get("soc_start"))
        wb_misurato = origine is None and kwh > 0
        if tipo == "Casa" and wb_misurato and delta_pct > 0.2:
            soh_ufficiale = max(self._setting_num("soh_official", 100.0), 50.0)
            teorica = delta_pct * self.capacity * (soh_ufficiale / 100.0) / 100.0
            eff = min(round(teorica / kwh * 100.0, 1), 100.0) if kwh > 0 else 0.0
            perdite = round(max(kwh - teorica, 0.0), 2)
            record["efficienza"] = eff
            record["perdite_kwh"] = perdite
            record["rete_kwh"] = round(kwh, 2)
            record["batteria_kwh"] = round(teorica, 2)
            health = self.store.data.setdefault("health", {})
            health["last_eff"] = eff
            health["last_perdite_kwh"] = perdite
            health["last_rete_kwh"] = round(kwh, 2)
            health["last_batteria_kwh"] = round(teorica, 2)
            health["last_delta_pct"] = round(delta_pct, 1)
            # stima SOH solo con una ricarica SIGNIFICATIVA (>=15%): sotto, il rapporto
            # kWh/% è troppo sensibile agli errori e può superare il 100%.
            if delta_pct >= 15:
                soh = round((kwh * 0.92 / delta_pct) * (100.0 / self.capacity) * 100.0, 1)
                health["soh_stimato"] = min(soh, 100.0)
            sessions = health.setdefault("sessions", [])
            sessions.append({
                "id": record["id"], "data": record["data"], "eff": eff,
                "perdite_kwh": perdite, "delta_pct": round(delta_pct, 1), "kwh": record["kwh"],
            })
            del sessions[:-100]

        self.store.data["charges"].append(record)
        # costo totale = somma delle ricariche registrate (fonte di verità, niente doppi conteggi)
        self.cost_total = round(
            sum(_f(c.get("costo")) for c in self.store.data["charges"]), 2
        )
        self.charge_session = None
        self._charge_off_polls = 0
        self.persist(force=True)
        return record

    # ------------------------------------------------------------- arricchimenti
    def _zone_label(self, raw: str) -> str:
        """Traduce lo stato del tracker (home/not_home/zona) nel nome leggibile della zona HA."""
        z = str(raw or "").strip()
        if not z:
            return "—"
        zone = self.hass.states.get(f"zone.{z}")
        if zone is not None:
            return str(zone.attributes.get("friendly_name") or z)
        if z == "home":
            home = self.hass.states.get("zone.home")
            return str((home.attributes.get("friendly_name") if home else None) or "Casa")
        if z in ("not_home", "unknown", "unavailable"):
            return "Fuori"
        return z.replace("_", " ").title()

    def _enrich_trip(self, record: dict[str, Any]) -> None:
        """Costo stimato, fonte ultima ricarica e DOPPIA VERIFICA con il GPS."""
        record["zona_partenza"] = self._zone_label(record.get("zona_partenza", ""))
        record["zona_arrivo"] = self._zone_label(record.get("zona_arrivo", ""))
        record["costo_stimato"] = round(_f(record.get("kwh_consumati")) * self.price_home, 2)
        # temperatura esterna all'arrivo: serve al grafico "consumi vs temperatura"
        if record.get("temp_est") is None:
            _t = self._read_temp()
            if _t is not None:
                record["temp_est"] = round(_f(_t), 1)
        # doppia verifica: coordinate reali del tracker all'arrivo + posizione aggiornata
        gps = {}
        posizione_aggiornata = False
        loc_entity = self.opts.get(CONF_LOCATION_ENTITY)
        if loc_entity:
            st = self.hass.states.get(loc_entity)
            if st is not None:
                lat = st.attributes.get("latitude")
                lon = st.attributes.get("longitude")
                if lat is not None and lon is not None:
                    gps = {"lat": round(_f(lat), 5), "lon": round(_f(lon), 5)}
                try:
                    ultima = st.last_updated
                    if ultima is not None and ultima.timestamp() >= self.trip.ts_start:
                        posizione_aggiornata = True
                except Exception:  # noqa: BLE001
                    pass
        record["gps_arrivo"] = gps
        record["verifica_posizione"] = posizione_aggiornata
        record["verifica"] = (
            "ok" if posizione_aggiornata else "gps non aggiornato (cloud Renault in ritardo)"
        )
        carica_prec = ""
        for c in reversed(self.store.data["charges"]):
            if c.get("data", "") < record.get("data", "") or (
                c.get("data") == record.get("data")
                and str(c.get("ora_fine", "")) <= record.get("ora_inizio", "")
            ):
                carica_prec = str(c.get("tipo", ""))
                break
        record["carica_precedente"] = carica_prec

    # ------------------------------------------------------ reverse geocoding GPS
    def _queue_geocode(self, record: dict[str, Any]) -> None:
        """Avvia in background il reverse-geocoding partenza+arrivo (non blocca il ciclo)."""
        if not self.geocode_enabled:
            return
        if record.get("luogo_partenza") and record.get("luogo_arrivo"):
            return
        if not (record.get("gps_partenza") or record.get("gps_arrivo")):
            return
        try:
            self.hass.async_create_task(self._geocode_trip(record))
        except RuntimeError:  # nessun event loop attivo
            pass

    async def _reverse_geocode(self, lat: float, lon: float) -> dict[str, str]:
        """Coordinate → {via, citta, paese, label} via Nominatim/OSM, con cache su disco."""
        if not self.geocode_enabled:
            return {}
        lat4, lon4 = round(_f(lat), 4), round(_f(lon), 4)
        key = f"{lat4},{lon4}"
        cache = self.store.data.setdefault("geocache", {})
        if key in cache:
            return cache[key]
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        url = ("https://nominatim.openstreetmap.org/reverse?format=jsonv2"
               f"&lat={lat4}&lon={lon4}&zoom=16&addressdetails=1&accept-language=it")
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                url, headers={"User-Agent": "renault-ev-center/1.0 (Home Assistant)"}, timeout=6
            ) as resp:
                if resp.status != 200:
                    return {}
                js = await resp.json()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Reverse geocoding non riuscito: %s", err)
            return {}
        ad = js.get("address") or {}
        via = ad.get("road") or ad.get("pedestrian") or ad.get("suburb") or ""
        citta = (ad.get("city") or ad.get("town") or ad.get("village")
                 or ad.get("municipality") or ad.get("county") or "")
        paese = ad.get("country") or ""
        out = {"via": via, "citta": citta, "paese": paese,
               "label": ", ".join(p for p in (via, citta) if p)}
        cache[key] = out
        if len(cache) > 500:
            for k in list(cache)[: len(cache) - 500]:
                cache.pop(k, None)
        self.persist()
        return out

    async def _geocode_trip(self, record: dict[str, Any]) -> None:
        """Scrive via/città/paese di partenza e arrivo sul viaggio (best-effort)."""
        for gkey, lkey, pkey in (("gps_partenza", "luogo_partenza", "paese_partenza"),
                                 ("gps_arrivo", "luogo_arrivo", "paese_arrivo")):
            if record.get(lkey):
                continue
            gps = record.get(gkey) or {}
            lat, lon = gps.get("lat"), gps.get("lon")
            if lat is None or lon is None:
                continue
            info = await self._reverse_geocode(lat, lon)
            if info:
                record[lkey] = info.get("label") or info.get("citta") or ""
                record[pkey] = info.get("paese") or ""
        self.persist()

    def _maybe_backfill_geocode(self) -> None:
        """Una tantum: geocodifica i viaggi registrati prima che il geocoding esistesse."""
        if self._geocode_backfilled or not self.geocode_enabled:
            return
        self._geocode_backfilled = True
        legacy = [t for t in self.store.data.get("trips", [])
                  if (t.get("gps_partenza") or t.get("gps_arrivo"))
                  and not (t.get("luogo_partenza") and t.get("luogo_arrivo"))]
        if legacy:
            self.hass.async_create_task(self._geocode_backfill())

    async def _geocode_backfill(self) -> None:
        """Geocodifica i viaggi vecchi, 1 alla volta (rispetta il limite ~1 req/s)."""
        n = 0
        for t in self.store.data.get("trips", []):
            if t.get("luogo_partenza") and t.get("luogo_arrivo"):
                continue
            if not (t.get("gps_partenza") or t.get("gps_arrivo")):
                continue
            await self._geocode_trip(t)
            n += 1
            if n >= 120:
                break
            await asyncio.sleep(1.1)
        if n:
            _LOGGER.info("Geocoding: rielaborati %s viaggi", n)
        self.persist()

    def _filter_charges(self, charges: list[dict], now) -> dict[str, Any]:
        """Filtra le ricariche secondo i select tipo/periodo/anno e calcola i totali."""
        tipo = self._setting_opt("filtro_tipo", "Tutte")
        periodo = self._setting_opt("filtro_periodo", "Mese")
        mese = self._setting_opt("filtro_mese", "Tutti")
        anno = self._setting_opt("filtro_anno", "Tutti")
        d = now.date()
        if periodo == "Settimana":
            start = (d - timedelta(days=d.weekday())).isoformat()
        elif periodo == "Mese":
            start = d.replace(day=1).isoformat()
        elif periodo == "Anno":
            start = d.replace(month=1, day=1).isoformat()
        else:
            start = ""
        num_mese = MESI_FILTRO.index(mese) if mese in MESI_FILTRO else 0  # 0 = Tutti
        items = []
        for c in charges:
            if tipo != "Tutte" and c.get("tipo") != tipo:
                continue
            if anno != "Tutti" and str(c.get("data", ""))[:4] != anno:
                continue
            if num_mese and str(c.get("data", ""))[5:7] != f"{num_mese:02d}":
                continue
            if start and str(c.get("data", "")) < start:
                continue
            items.append(c)
        items.sort(key=lambda c: (str(c.get("data", "")), str(c.get("ora_inizio", ""))), reverse=True)
        return {
            "items": items[:300],
            "n": len(items),
            "kwh": round(sum(_f(c.get("kwh")) for c in items), 2),
            "costo": round(sum(_f(c.get("costo")) for c in items), 2),
            "tipo": tipo,
            "periodo": periodo,
            "mese": mese,
            "anno": anno,
        }

    def _build_report(self, now, keys: dict[str, str], today_key: str) -> dict[str, Any]:
        """Tabelle Generale / Settimanale / Mensile (costo, kWh caricati, km)."""
        charges = self.store.data["charges"]
        history = {d.get("data"): d for d in self.store.data["daily"]}
        arch_mese = self.store.data.get("monthly_km", {})

        costo_giorno: dict[str, float] = {}
        kwh_giorno: dict[str, float] = {}
        for c in charges:
            g = str(c.get("data", ""))
            if not g:
                continue
            costo_giorno[g] = costo_giorno.get(g, 0.0) + _f(c.get("costo"))
            kwh_giorno[g] = kwh_giorno.get(g, 0.0) + _f(c.get("kwh"))

        ieri = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        mese_key = keys["monthly"]
        anno_key = keys["yearly"]

        def km_di(giorno: str) -> float:
            if giorno == today_key:
                return _f(self.km_meters["daily"].value)
            rec = history.get(giorno)
            return _f(rec.get("km")) if rec else 0.0

        def somma_per(mappa: dict, prefisso: str) -> float:
            return round(sum(v for g, v in mappa.items() if g[:7] == prefisso), 2)

        generale = [
            {"periodo": "Ieri", "costo": round(costo_giorno.get(ieri, 0.0), 2),
             "kwh": round(kwh_giorno.get(ieri, 0.0), 2),
             "km": round(_f(self.km_meters["daily"].last), 0)},
            {"periodo": "Oggi", "costo": round(costo_giorno.get(today_key, 0.0), 2),
             "kwh": round(kwh_giorno.get(today_key, 0.0), 2),
             "km": round(km_di(today_key), 0)},
            {"periodo": "Mese", "costo": somma_per(costo_giorno, mese_key),
             "kwh": somma_per(kwh_giorno, mese_key),
             "km": round(_f(self.km_meters["monthly"].value), 0)},
            {"periodo": "Anno", "costo": somma_per(costo_giorno, anno_key),
             "kwh": somma_per(kwh_giorno, anno_key),
             "km": round(_f(self.km_meters["yearly"].value), 0)},
        ]

        giorni_it = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
        lunedi = (now.date() - timedelta(days=now.weekday()))
        settimanale = []
        for i in range(7):
            g = (lunedi + timedelta(days=i)).isoformat()
            settimanale.append({
                "giorno": giorni_it[i], "data": g,
                "costo": round(costo_giorno.get(g, 0.0), 2),
                "kwh": round(kwh_giorno.get(g, 0.0), 2),
                "km": round(km_di(g), 0),
            })

        mesi_it = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                   "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        # anno selezionato dal Filtro Anno (default: corrente)
        anno_sel = self._setting_opt("filtro_anno", str(now.year))
        if not (anno_sel.isdigit() and len(anno_sel) == 4):
            anno_sel = str(now.year)
        anno_corrente = str(now.year)
        mensile = []
        for m in range(1, 13):
            mk = "%s-%02d" % (anno_sel, m)
            if mk in arch_mese:
                # dall'archivio permanente (affidabile anche per anni passati)
                km_tot = _f(arch_mese.get(mk))
            else:
                km_tot = 0.0
                for g, rec in history.items():
                    if g[:7] == mk:
                        km_tot += _f(rec.get("km"))
                # il mese corrente dell'anno selezionato usa anche i dati live di oggi
                if mk == mese_key:
                    km_tot += _f(self.km_meters["daily"].value)
            mensile.append({
                "mese": mesi_it[m - 1],
                "anno": anno_sel,
                "costo": somma_per(costo_giorno, mk),
                "kwh": somma_per(kwh_giorno, mk),
                "km": round(km_tot, 0),
            })

        solare = []
        for m in range(1, 13):
            mk = "%s-%02d" % (anno_sel, m)
            casa = round(sum(_f(c.get("kwh")) for c in charges
                             if c.get("tipo") == "Casa" and str(c.get("data", ""))[:7] == mk), 2)
            fv = round(sum(_f(c.get("kwh")) for c in charges
                           if c.get("tipo") == "Fotovoltaico" and str(c.get("data", ""))[:7] == mk), 2)
            pub = round(sum(_f(c.get("kwh")) for c in charges
                            if c.get("tipo") == "Pubblica" and str(c.get("data", ""))[:7] == mk), 2)
            solare.append({"mese": mesi_it[m - 1], "casa": casa, "fv": fv,
                           "pubblica": pub, "tot": round(casa + fv + pub, 2)})
        return {"generale": generale, "settimanale": settimanale, "mensile": mensile,
                "solare": solare, "anno": anno_sel, "anno_corrente": anno_corrente}

    # ---------------------------------------------------------------- servizi
    def service_close_trip(self) -> dict[str, Any] | None:
        """Chiude subito il viaggio attivo."""
        if not self.trip.active:
            return None
        location = (_txt(self.hass, self.opts.get(CONF_LOCATION_ENTITY)) or "").lower()
        eff = _f(self.data.get("eff_kwh_100km")) if self.data else 0.0
        rec = self.trip.close(location, eff, __import__("time").time())
        if rec is not None:
            self.store.data["trips"].append(rec)
        self.persist(force=True)
        return rec

    def service_reset_counters(self, scope: str) -> None:
        """Reset dei contatori: km | energia | costi | viaggi | ricariche | all."""
        now = dt_util.now()
        keys = period_keys(now)
        odometer = _num(self.hass, self.opts.get(CONF_ODOMETER))

        if scope in ("km", "all"):
            for p in PERIODS:
                mm = self.km_meters[p]
                mm.value = 0.0
                mm.last = 0.0
                mm.key = keys[p]
                mm.baseline = odometer if odometer > 0 else None
        if scope in ("energia", "all"):
            for p in PERIODS:
                wm = self.wb_meters[p]
                wm.value = 0.0
                wm.last = 0.0
                wm.key = keys[p]
                wm.ref_last = self._wb_counter()
                for d in ("up", "down"):
                    kd = self.kwh_meters[p][d]
                    kd.value = 0.0
                    kd.last = 0.0
                    kd.key = keys[p]
                    kd.ref_last = None
            for d in ("up", "down"):
                pd = self.pct_daily[d]
                pd.value = 0.0
                pd.last = 0.0
                pd.ref_last = None
        if scope in ("costi", "all"):
            for p in PERIODS:
                self.cost_meters[p] = _new_cost_meter()
            self.cost_total = 0.0
        if scope in ("viaggi", "all"):
            self.store.data["trips"] = []
            self.trip.active = False
        if scope in ("ricariche", "all"):
            self.store.data["charges"] = []
            self.charge_session = None
        self.persist(force=True)

    def service_add_manual_charge(self, kwh: float, costo: float, tipo: str,
                                  quando: datetime | None, descrizione: str = "") -> dict[str, Any]:
        q = quando or dt_util.now()
        record = {
            "id": int(q.timestamp()),
            "data": q.strftime("%Y-%m-%d"),
            "ora_inizio": q.strftime("%H:%M"),
            "ora_fine": q.strftime("%H:%M"),
            "durata_min": 0,
            "kwh": round(kwh, 2),
            "soc_start": 0.0,
            "soc_end": 0.0,
            "potenza_media_kw": 0.0,
            "costo": round(costo, 2),
            "tipo": tipo or "Manuale",
            "note": str(descrizione or "").strip(),
        }
        self.store.data["charges"].append(record)
        self.cost_total = round(
            sum(_f(c.get("costo")) for c in self.store.data["charges"]), 2
        )
        self.persist(force=True)
        return record

    def service_delete_trip(self, trip_id: int) -> bool:
        prima = len(self.store.data["trips"])
        self.store.data["trips"] = [t for t in self.store.data["trips"] if t.get("id") != trip_id]
        self.persist(force=True)
        return len(self.store.data["trips"]) < prima

    def service_add_maintenance(self, data: str = "", km: float | None = None, costo: float = 0.0,
                                tipo: str = "Tagliando", note: str = "") -> dict[str, Any]:
        """Registra una manutenzione (data e/o km opzionali)."""
        from datetime import date as _date

        record = {
            "id": int(time.time()),
            "data": data or _date.today().isoformat(),
            "km": round(km, 0) if km else 0.0,
            "costo": round(costo, 2),
            "tipo": tipo or "Tagliando",
            "note": note or "",
        }
        self.store.data.setdefault("maintenance", []).append(record)
        self.store.data["maintenance"].sort(key=lambda m: m.get("data", ""))
        self.persist(force=True)
        return record

    def service_set_maintenance(self, tipo: str, km: float | None, data: str) -> dict[str, Any]:
        """Imposta la prossima scadenza per un tipo (tagliando/gomme): km e/o data."""
        scad = self.store.data.setdefault("scadenze", {})
        key = "gomme" if tipo == "gomme" else "tagliando"
        if km is not None:
            scad[f"{key}_km"] = float(km)
        else:
            scad.pop(f"{key}_km", None)
        if data:
            scad[f"{key}_data"] = data
        else:
            scad.pop(f"{key}_data", None)
        self.persist(force=True)
        return {k: v for k, v in scad.items() if k.startswith(key)}

    def service_delete_maintenance(self, maint_id: int) -> bool:
        prima = len(self.store.data.get("maintenance", []))
        self.store.data["maintenance"] = [
            m for m in self.store.data["maintenance"] if m.get("id") != maint_id
        ]
        self.persist(force=True)
        return len(self.store.data.get("maintenance", [])) < prima

    # ------------------------------------------------- scadenze / notifiche
    def service_renew_insurance(self, mesi: int = 12, data: str = "") -> str:
        """Rinnova l'assicurazione: da oggi +mesi oppure data specifica (YYYY-MM-DD)."""
        from datetime import date as _date

        if data:
            nuova = str(data)
        else:
            oggi = _date.today()
            m = oggi.month - 1 + int(mesi)
            anno = oggi.year + m // 12
            mese = m % 12 + 1
            nuova = ""
            for g in (oggi.day, 30, 28):
                try:
                    nuova = _date(anno, mese, g).isoformat()
                    break
                except ValueError:
                    continue
        scad = self.store.data.setdefault("scadenze", {})
        scad["assicurazione"] = nuova
        self.persist(force=True)
        return nuova

    def service_set_scadenza(self, nome: str, data: str) -> str:
        """Imposta una scadenza per nome: assicurazione|bollo|revisione|tagliando_data."""
        chiavi = {"assicurazione", "bollo", "revisione", "tagliando_data"}
        if nome not in chiavi:
            raise ValueError(f"nome deve essere uno di {chiavi}")
        scad = self.store.data.setdefault("scadenze", {})
        scad[nome] = data
        self.persist(force=True)
        return data

    def service_set_tagliando(self, mode: str, valore: str) -> str:
        """Modalità tagliando: 'km' (prossimo a km assoluti) o 'data' (YYYY-MM-DD)."""
        if mode not in ("km", "data"):
            raise ValueError("mode deve essere km o data")
        scad = self.store.data.setdefault("scadenze", {})
        scad["tagliando_mode"] = mode
        if mode == "km":
            scad["tagliando_km"] = float(valore)
        else:
            scad["tagliando_data"] = valore
        self.persist(force=True)
        return mode

    def service_set_low_soc_days(self, days: list[str]) -> list[str]:
        """Imposta i giorni della settimana dell'avviso batteria bassa."""
        validi = [d for d in (days or []) if d in WEEKDAYS]
        opts = dict(self.entry.options)
        opts[CONF_LOW_SOC_DAYS] = validi
        self.hass.config_entries.async_update_entry(self.entry, options=opts)
        self.low_soc_days = validi
        return validi

    async def service_create_automations(self) -> list[str]:
        """Crea (solo se assenti) le automazioni consigliate in automations.yaml."""
        from .dashboard import slugify

        n = slugify(str(self.opts.get(CONF_NAME, "Renault")))
        batt = str(self.opts.get("battery_level_entity") or f"sensor.{n}_batteria")
        range_e = str(self.opts.get("range_entity") or f"sensor.{n}_autonomia_della_batteria")
        # il nostro binary_sensor è SEMPRE on/off: l'entità sorgente può essere un sensore
        # testuale ("charging"/"not_charging") e il trigger from on → off non scatterebbe mai
        charging = f"binary_sensor.{n}_in_carica"
        loc = str(self.opts.get("location_entity") or "")
        wb_state_e = str(self.opts.get(CONF_WB_STATE) or "sensor.wallbox_charger_state")
        target = ""
        if self.notify_service:
            target = self.notify_service if "." in self.notify_service else f"notify.{self.notify_service}"

        def _pn(notif_id: str, title: str, msg: str) -> dict:
            if target:
                return {"action": target, "data": {"title": title, "message": msg}}
            return {"action": "persistent_notification.create",
                    "data": {"notification_id": notif_id, "title": title, "message": msg}}

        autos: dict[str, dict] = {
            f"renault_ev_center_{n}_ricarica_completata": {
                "alias": f"Renault EV Center — Ricarica completata ({n})",
                "trigger": [{"trigger": "state", "entity_id": charging,
                              "from": "on", "to": "off", "for": {"minutes": 3}}],
                # NIENTE condizione sulla data: una ricarica notturna inizia ieri e finisce oggi,
                # quindi il confronto con la data di OGGI la scartava (notifica mai inviata).
                "action": [_pn(f"rec_ric_{n}", "🔋 Ricarica completata",
                                "⚡ {{ states('sensor." + n + "_ultima_ricarica') }} kWh · "
                                "🔋 {{ state_attr('sensor." + n + "_ultima_ricarica', 'soc_end') }}% · "
                                "💰 {{ state_attr('sensor." + n + "_ultima_ricarica', 'costo') }} € · "
                                "📍 {{ state_attr('sensor." + n + "_ultima_ricarica', 'zona') or '—' }}")],
                "mode": "single",
            },
            f"renault_ev_center_{n}_avvio_ricarica": {
                "alias": f"Renault EV Center — Notifica avvio ricarica ({n})",
                "trigger": [{"trigger": "state", "entity_id": wb_state_e, "to": "charging"}],
                "condition": [],
                "action": [_pn(f"rec_start_{n}", "🔋 Ricarica avviata",
                                "La ricarica è iniziata alle {{ now().strftime('%d-%m-%Y %H:%M') }}")],
                "mode": "single",
            },
            f"renault_ev_center_{n}_riassunto_giornaliero": {
                "alias": f"Renault EV Center — Riassunto giornaliero ({n})",
                "trigger": [{"trigger": "time", "at": "21:30:00"}],
                "condition": [{"condition": "numeric_state",
                                "entity_id": f"sensor.{n}_km_giornalieri", "above": 0.5}],
                "action": [_pn(f"rec_sum_{n}", "📊 Oggi con la tua Renault",
                                "{% set kwh = states('sensor." + n + "_energia_batteria_giornaliero') | float(none) %}"
                                "{% set prezzo = states('number." + n + "_costo_energia_casa') | float(none) %}"
                                "Km oggi: {{ states('sensor." + n + "_km_giornalieri') }} km\n"
                                "Energia consumata oggi: {% if kwh is not none %}{{ kwh | round(2) }} kWh"
                                "{% else %}non disponibile{% endif %}\n"
                                "Costo totale energia oggi (stimato, tariffa casa): "
                                "{% if kwh is not none and prezzo is not none %}{{ (kwh * prezzo) | round(2) }} €"
                                "{% else %}non disponibile{% endif %}\n"
                                "Consumo: {{ states('sensor." + n + "_kwh_per_100km') }} kWh/100km · "
                                "Costo/km: {{ states('sensor." + n + "_costo_per_km') }} €/km")],
                "mode": "single",
            },
            f"renault_ev_center_{n}_refresh_auto": {
                "alias": f"Renault EV Center — Aggiorna posizione auto ({n})",
                "trigger": [{"trigger": "time_pattern", "minutes": "/30"}],
                "condition": [],
                "action": [{"action": "renault_ev_center.refresh_car"}],
                "mode": "single",
            },
        }

        # la notifica "batteria bassa" è gestita NATIVAMENTE dall'integrazione (soglia, fascia
        # oraria e giorni configurabili dalla vista Automazioni): l'automazione omonima va rimossa
        return await self._automations_apply(
            autos,
            [f"renault_ev_center_{n}_promemoria", f"renault_ev_center_{n}_batteria_bassa"],
        )

    async def _automations_apply(self, upserts: dict[str, dict], removes: list[str]) -> list[str]:
        """Scrive/aggiorna/rimuove automazioni in automations.yaml (come la UI HA)."""
        from homeassistant.config import AUTOMATION_CONFIG_PATH
        from homeassistant.util.file import write_utf8_file_atomic
        from homeassistant.util.yaml import dump as _yaml_dump
        from homeassistant.util.yaml import load_yaml as _yaml_load

        from .dashboard import slugify

        nome = slugify(str(self.opts.get(CONF_NAME, "Renault")))
        # suffissi gestiti dall'integrazione: un id con slug diverso è un orfano (nome auto cambiato)
        gestiti = ("_ricarica_completata", "_avvio_ricarica", "_batteria_bassa",
                   "_riassunto_giornaliero", "_promemoria", "_programma_ricarica",
                   "_programma_clima", "_scadenze", "_promemoria_batteria", "_refresh_auto")

        def _orfana(aid: object) -> bool:
            if not isinstance(aid, str) or not aid.startswith("renault_ev_center_"):
                return False
            if any(aid == f"renault_ev_center_{nome}{s}" for s in gestiti):
                return False
            return any(aid.endswith(s) for s in gestiti)

        def _legacy(entry: object) -> bool:
            """Automazioni NON più create dall'integrazione: vanno rimosse.

            - 'batteria bassa' / 'batteria bassa fuori casa': sostituite dalla notifica NATIVA
              (soglia, fascia oraria e giorni configurabili dalla vista Automazioni);
            - 'promemoria collegamento': ridondante — la notifica «Avviso batteria bassa» dice
              già «Collega la wallbox!».

            Match su id O alias: i residui vecchi possono avere id diversi.
            """
            if not isinstance(entry, dict):
                return False
            aid = str(entry.get("id") or "")
            alias = str(entry.get("alias") or "").lower()
            if not (aid.startswith("renault_ev_center_") or "renault ev center" in alias):
                return False
            return (aid.endswith("_batteria_bassa") or "_batteria_bassa_" in aid
                    or aid.endswith("_programma_promemoria") or "_promemoria_collegamento" in aid
                    or "batteria bassa fuori casa" in alias
                    or "promemoria collegamento" in alias)

        path = self.hass.config.path(AUTOMATION_CONFIG_PATH)
        rmset = set(removes)

        def _eid(cfg: dict) -> str:
            return f"automation.{slugify(str(cfg.get('alias', '')))}"

        # stato on/off di TUTTE le automazioni PRIMA del reload: `automation.reload`
        # riaccende tutto, quindi va ripristinata la scelta dell'utente (non solo le salvate).
        prev_auto: dict[str, str] = {
            s.entity_id: s.state for s in self.hass.states.async_all("automation")
        }
        prev_state: dict[str, str | None] = {
            aid: prev_auto.get(_eid(cfg)) for aid, cfg in upserts.items()
        }

        def _apply() -> list[str]:
            try:
                data = _yaml_load(path)
            except Exception:  # noqa: BLE001
                data = None
            if not isinstance(data, list):
                data = []
            n_before = len(data)
            data = [d for d in data if not (isinstance(d, dict) and d.get("id") in rmset)]
            data = [d for d in data if not (isinstance(d, dict) and _legacy(d))]
            data = [d for d in data if not (isinstance(d, dict) and _orfana(d.get("id")))]
            purged = len(data) != n_before   # legacy/orfane rimosse → va riscritto
            byid = {d.get("id"): i for i, d in enumerate(data) if isinstance(d, dict) and d.get("id")}
            made: list[str] = []
            for aid, cfg in upserts.items():
                entry = {"id": aid, **cfg}
                if aid in byid:
                    data[byid[aid]] = entry
                else:
                    data.append(entry)
                made.append(aid)
            if made or rmset or purged:
                write_utf8_file_atomic(path, _yaml_dump(data))
            return made, purged

        changed, purged = await self.hass.async_add_executor_job(_apply)
        if changed or rmset or purged:
            await self.hass.services.async_call("automation", "reload", {}, blocking=True)
            # 1) ripristina TUTTE le automazioni che l'utente aveva spento (il reload le riaccende)
            for eid, stt in prev_auto.items():
                if stt == "off" and self.hass.states.get(eid) is not None:
                    await self.hass.services.async_call(
                        "automation", "turn_off", {"entity_id": eid}, blocking=False)
            # 2) accendi SOLO le automazioni appena create
            for aid, cfg in upserts.items():
                if prev_state.get(aid) is None:
                    eid = _eid(cfg)
                    if self.hass.states.get(eid) is not None:
                        await self.hass.services.async_call(
                            "automation", "turn_on", {"entity_id": eid}, blocking=False)
        return changed

    async def service_set_schedule(self, tipo: str, attivo: bool, inizio: str,
                                   fine: str, soc: int, modo: str, temperatura: int,
                                   giorni: list[str]) -> list[str]:
        """Crea/aggiorna l'automazione di schedulazione ricarica o clima."""
        from .dashboard import slugify

        n = slugify(str(self.opts.get(CONF_NAME, "Renault")))
        aid = f"renault_ev_center_{n}_programma_{tipo}"
        # memorizzo i valori: il pannello li usa per ripopolare il form dopo un refresh
        self.store.data.setdefault("schedule", {})[tipo] = {
            "attivo": bool(attivo), "inizio": str(inizio), "fine": str(fine),
            "soc": int(soc or 0), "modo": str(modo), "temperatura": int(temperatura or 0),
            "giorni": list(giorni or []),
        }
        self.persist(force=True)
        if not attivo:
            return await self._automations_apply({}, [aid])

        days = [d for d in (giorni or []) if d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")]
        cond = [{"condition": "time", "weekday": days}] if days else []

        if tipo == "ricarica":
            actions: list[dict] = []
            tgt = self.opts.get(CONF_CHARGE_TARGET_NUMBER)
            if soc and tgt:
                actions.append({"action": "number.set_value",
                                "target": {"entity_id": tgt}, "data": {"value": int(soc)}})
            wb = self.opts.get(CONF_WB_CHARGE_SWITCH)
            btn = self.opts.get(CONF_CHARGE_START_BUTTON)
            ent = wb or btn
            if not ent:
                # senza entità di avvio l'automazione non farebbe NULLA: provo i nomi comuni
                for cand in ("button.wallbox_charger_start", f"button.{n}_start_charge"):
                    if self.hass.states.get(cand) is not None:
                        ent = cand
                        break
            if ent:
                dom = str(ent).split(".")[0]
                if dom == "switch":
                    actions.append({"action": "switch.turn_on", "target": {"entity_id": ent}})
                elif dom == "button":
                    actions.append({"action": "button.press", "target": {"entity_id": ent}})
                else:
                    actions.append({"action": "homeassistant.turn_on", "target": {"entity_id": ent}})
            if not actions:
                _LOGGER.error(
                    "Programma ricarica: NESSUNA azione possibile — mappa 'Avvio carica WALLBOX' "
                    "(o il Pulsante Avvia carica) in Configura, altrimenti l'automazione non fa nulla"
                )
            cfg = {"alias": f"Renault EV Center — Programma ricarica ({n})",
                   "trigger": [{"trigger": "time", "at": f"{inizio}:00"}],
                   "condition": cond, "action": actions, "mode": "single"}
        elif tipo == "promemoria":
            target = ""
            if self.notify_service:
                target = self.notify_service if "." in self.notify_service else f"notify.{self.notify_service}"
            act = ({"action": target, "data": {"title": "🔌 Ricarica", "message": "Ricordati di collegare l'auto alla ricarica."}}
                   if target else
                   {"action": "persistent_notification.create",
                    "data": {"notification_id": f"rec_plug_{n}", "title": "🔌 Ricarica",
                             "message": "Ricordati di collegare l'auto alla ricarica."}})
            cfg = {"alias": f"Renault EV Center — Promemoria collegamento ({n})",
                   "trigger": [{"trigger": "time", "at": f"{inizio}:00"}],
                   "condition": cond, "action": [act], "mode": "single"}
        else:
            btn = self.opts.get(CONF_AC_BUTTON)
            cfg = {"alias": f"Renault EV Center — Programma clima ({n})",
                   "trigger": [{"trigger": "time", "at": f"{inizio}:00"}],
                   "condition": cond,
                   "action": [{"action": "button.press", "target": {"entity_id": btn}}] if btn else [],
                   "mode": "single"}
        made = await self._automations_apply({aid: cfg}, [])
        # l'automazione appena salvata deve essere ATTIVA, altrimenti non parte mai
        await self._enable_automation(cfg["alias"])
        return made

    async def async_sync_schedule_from_automation(self) -> None:
        """Riprende orario, giorni e SoC della carica programmata DALL'automazione esistente.

        Così le scelte NON si perdono dopo un aggiornamento/riavvio: se lo store non ha
        l'orario (o ha SoC 0), li legge dal trigger e dall'azione dell'automazione.
        """
        from homeassistant.config import AUTOMATION_CONFIG_PATH
        from homeassistant.util.yaml import load_yaml as _yaml_load

        from .dashboard import slugify

        sch = self.store.data.setdefault("schedule", {})
        cur = dict(sch.get("ricarica") or {})
        path = self.hass.config.path(AUTOMATION_CONFIG_PATH)
        try:
            data = await self.hass.async_add_executor_job(_yaml_load, path)
        except Exception:  # noqa: BLE001
            return
        n = slugify(str(self.opts.get(CONF_NAME, "Renault")))
        aid = f"renault_ev_center_{n}_programma_ricarica"
        autos = data if isinstance(data, list) else []
        for a in autos:
            if not (isinstance(a, dict) and a.get("id") == aid):
                continue
            trig = a.get("trigger") or a.get("triggers") or []
            if isinstance(trig, dict):
                trig = [trig]
            if not isinstance(trig, list):
                trig = []
            giorni: list[str] = []
            for c in (a.get("condition") or a.get("conditions") or []):
                if isinstance(c, dict) and c.get("weekday"):
                    wd = c["weekday"]
                    giorni = [wd] if isinstance(wd, str) else list(wd)
            # SoC obiettivo dall'azione number.set_value dell'automazione
            soc = 0
            for act in (a.get("action") or a.get("actions") or []):
                if isinstance(act, dict):
                    val = (act.get("data") or {}).get("value")
                    if val is not None:
                        try:
                            soc = int(float(val))
                        except (TypeError, ValueError):
                            pass
            for t in trig:
                at = str((t or {}).get("at") or "")[:5]
                if at:
                    cur["inizio"] = at
                    cur["giorni"] = giorni or cur.get("giorni", [])
                    if soc > 0:
                        cur["soc"] = soc
                    cur.setdefault("attivo", True)
                    cur.setdefault("fine", "")
                    cur.setdefault("modo", "cool")
                    cur.setdefault("temperatura", 0)
                    sch["ricarica"] = cur
                    self.persist(force=True)
                    _LOGGER.info("Carica programmata ripresa dall'automazione: %s · SoC %s%%",
                                 at, cur.get("soc"))
                    return

    async def async_cleanup_automations(self) -> None:
        """All'avvio rimuove le automazioni legacy (es. 'batteria bassa fuori casa').

        La notifica batteria bassa è gestita NATIVAMENTE: le automazioni omonime non servono.
        """
        try:
            await self._automations_apply({}, [])
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Pulizia automazioni fallita: %s", err)

    def _managed_auto_ids(self) -> list[str]:
        """Automazioni create dall'integrazione (per nome o entity_id)."""
        out: list[str] = []
        for s in self.hass.states.async_all("automation"):
            name = str(s.attributes.get("friendly_name") or "").lower()
            if "renault ev center" in name or "renault_ev_center" in s.entity_id:
                out.append(s.entity_id)
        return out

    def save_auto_states(self) -> None:
        """Seed iniziale: memorizza lo stato on/off delle automazioni gestite (una volta)."""
        states: dict[str, str] = {}
        for eid in self._managed_auto_ids():
            s = self.hass.states.get(eid)
            if s is not None:
                states[eid] = s.state
        if states and not self.store.data.get("auto_states"):
            self.store.data["auto_states"] = states
            self.persist()

    async def async_restore_auto_states(self) -> None:
        """IMPONE lo stato on/off scelto dall'utente: quelle spente restano spente.

        Gira a ogni ciclo (lo store è la fonte di verità): così HA non può riaccenderle
        al refresh/riavvio/update.
        """
        saved = self.store.data.get("auto_states") or {}
        for eid, stt in saved.items():
            if stt not in ("on", "off"):
                continue
            cur = self.hass.states.get(eid)
            if cur is not None and cur.state != stt:
                await self.hass.services.async_call(
                    "automation", "turn_on" if stt == "on" else "turn_off",
                    {"entity_id": eid}, blocking=False)

    async def service_set_auto_state(self, entity_id: str, state: str) -> None:
        """Accende/spegne un'automazione e MEMORIZZA la scelta (così non si riattiva più)."""
        saved = dict(self.store.data.get("auto_states") or {})
        saved[entity_id] = "on" if state == "on" else "off"
        self.store.data["auto_states"] = saved
        self.persist(force=True)
        # i servizi automation sono turn_on/turn_off: passare "on"/"off" produce
        # "La servizia automation.off non e stata trovata"
        await self.hass.services.async_call(
            "automation", "turn_on" if saved[entity_id] == "on" else "turn_off",
            {"entity_id": entity_id}, blocking=False)

    async def _enable_automation(self, alias: str) -> None:
        """Accende l'automazione (id derivato dall'alias) e lo segnala nel log."""
        from .dashboard import slugify

        eid = f"automation.{slugify(alias)}"
        st = self.hass.states.get(eid)
        if st is None:
            _LOGGER.warning("Automazione non trovata (%s): controlla che automations.yaml "
                            "sia incluso in configuration.yaml", eid)
            return
        if st.state == "on":
            return
        try:
            await self.hass.services.async_call(
                "automation", "turn_on", {"entity_id": eid}, blocking=False)
            _LOGGER.info("Automazione attivata: %s", eid)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Attivazione automazione fallita (%s): %s", eid, err)

    async def _check_notifications(self, scadenze: list[dict], oggi) -> None:
        """Invia una notifica al giorno se una scadenza rientra nel preavviso."""
        if not self.notify_service or not scadenze:
            return
        counters = self.store.data["counters"]
        today_key = oggi.strftime("%Y-%m-%d")
        if counters.get("last_notify") == today_key:
            return
        vicine = [s for s in scadenze if s["giorni"] <= self.notify_days]
        if not vicine:
            return
        righe = "\n".join(f"• {s['nome']}: {s['data']} (tra {s['giorni']} gg)" for s in vicine)
        await self._send_notify("🚗 Renault EV Center — Scadenze",
                                f"Scadenze in arrivo:\n{righe}")
        counters["last_notify"] = today_key
        self.persist(force=True)

    async def _send_notify(self, title: str, message: str) -> None:
        """Invia una notifica tramite il servizio notify configurato."""
        if not self.notify_service:
            return
        service = self.notify_service.split(".", 1)[-1] if "." in self.notify_service else self.notify_service
        try:
            await self.hass.services.async_call(
                "notify", service, {"title": title, "message": message}, blocking=True,
            )
            _LOGGER.info("Notifica inviata via %s", self.notify_service)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Notifica fallita (%s): %s — ritento senza title", self.notify_service, err)
            try:
                await self.hass.services.async_call(
                    "notify", service, {"message": f"{title}\n{message}"}, blocking=False,
                )
            except Exception as err2:  # noqa: BLE001
                _LOGGER.warning("Notifica fallback fallita (%s): %s", self.notify_service, err2)

    def _switch_on(self, key: str) -> bool:
        entity_id = self.setting_ids.get(f"switch.{key}")
        if entity_id:
            st = self.hass.states.get(entity_id)
            if st is not None:
                return st.state == "on"
        return False

    async def _wb_charge(self, avvia: bool, battery: float = 0.0) -> None:
        """Avvia/ferma la carica tramite la WALLBOX (switch o button).

        - switch: turn_on per avviare, turn_off per fermare
        - button: press (toggle) — usato solo se non c'è uno switch
        - fallback: number target di carica Renault (stop portando il target al SoC attuale)
        """
        ent = self.charge_start_button  # avvio (switch/button wallbox)
        # per FERMARE uso lo stop dedicato se mappato: un "button" di avvio ripremuto NON ferma
        target_ent = ent if avvia else (self.wb_stop_switch or ent)
        try:
            domain = target_ent.split(".")[0] if target_ent else ""
            if target_ent and domain == "switch":
                await self.hass.services.async_call(
                    "switch", "turn_on" if avvia else "turn_off",
                    {"entity_id": target_ent}, blocking=False,
                )
                _LOGGER.info("Carica programmata: wallbox %s", "avviata" if avvia else "fermata")
                return
            if target_ent and domain == "button":
                await self.hass.services.async_call(
                    "button", "press", {"entity_id": target_ent}, blocking=False,
                )
                _LOGGER.info("Carica programmata: pulsante %s premuto",
                             "avvio" if avvia else "stop")
                return
            # fallback: target Renault (solo per lo stop)
            if not avvia and self.charge_target_number:
                await self.hass.services.async_call(
                    "number", "set_value",
                    {"entity_id": self.charge_target_number, "value": max(int(battery), 0)},
                    blocking=False,
                )
                _LOGGER.info("Carica programmata: target Renault impostato a %s%%", int(battery))
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Comando carica programmata fallito: %s", err)

    def _gse_info(self) -> dict[str, Any]:
        """Stato della sperimentazione GSE per il pannello."""
        attivo = self._switch_on("gse")
        info: dict[str, Any] = {
            "attivo": attivo,
            "fascia": f"{self.gse_start}–{self.gse_end}",
            "kw_piena": self.gse_kw_max,
            "kw_ridotta": self.gse_kw_ridotta,
            "domenica": self.gse_domenica,
        }
        if attivo:
            kw = self._gse_limite_kw(dt_util.now())
            info["kw_adesso"] = kw
            info["in_fascia"] = kw >= self.gse_kw_max
        return info

    def _gse_limite_kw(self, now) -> float:
        """Potenza consentita dalla sperimentazione GSE in questo momento."""
        if self.gse_domenica and now.weekday() == 6:      # domenica
            return self.gse_kw_max
        if self.gse_holiday:
            st = self.hass.states.get(self.gse_holiday)
            if st is not None and st.state == "on":       # festivo
                return self.gse_kw_max
        hhmm = now.strftime("%H:%M")
        s, e = self.gse_start, self.gse_end
        dentro = (s <= hhmm or hhmm < e) if s > e else (s <= hhmm < e)
        return self.gse_kw_max if dentro else self.gse_kw_ridotta

    async def _apply_gse(self, wb_state: str, charging: bool) -> None:
        """Sperimentazione GSE: fuori fascia abbassa la corrente della wallbox.

        Fascia a potenza piena: da `gse_start` a `gse_end` nei feriali, tutta la domenica
        (e i festivi se mappati). Fuori fascia: potenza ridotta (es. 3 kW).
        """
        if not self._switch_on("gse"):
            return
        ent = self.opts.get(CONF_WB_MAX_CURRENT)
        if not ent:
            return
        if wb_state not in WALLBOX_CHARGING_STATES and not charging:
            return
        kw = self._gse_limite_kw(dt_util.now())
        amps = int(round(kw * 1000.0 / self.gse_wpa))
        amps = max(amps, 6)                               # minimo di una wallbox
        cur = _num(self.hass, str(ent), None)
        if cur is not None and abs(cur - amps) < 0.5:
            return                                        # già corretto: nessuna chiamata
        try:
            await self.hass.services.async_call(
                "number", "set_value", {"entity_id": ent, "value": amps}, blocking=False)
            _LOGGER.info("Sperimentazione GSE: %.1f kW → %s A", kw, amps)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("GSE: impostazione corrente fallita: %s", err)

    async def _balance_solar(self, data: dict[str, Any], wb_state: str) -> None:
        """Bilanciamento solare dinamico (adattato dall'automazione utente).

        Ogni ciclo: surplus disponibile = esportazione rete (+ eventuale scarica
        batteria se inclusa). Corregge gli ampere della wallbox per mantenere
        il prelievo da rete ~0, con isteresi di 1 A e pausa minima 60 s.
        """
        if not self._switch_on("balance"):
            return
        if wb_state not in WALLBOX_CHARGING_STATES or not self.balance_grid_sensor:
            return
        max_entity = self.opts.get(CONF_WB_MAX_CURRENT)
        if not max_entity:
            _LOGGER.warning("Bilanciamento: mappa il number corrente wallbox in configurazione")
            return
        now_t = time.time()
        if now_t - self._balance_last_change < 60:
            return

        st_grid = self.hass.states.get(self.balance_grid_sensor)
        if st_grid is None or st_grid.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        grid_w = _f(st_grid.state)
        if self.balance_invert_grid:
            grid_w = -grid_w
        surplus = -grid_w  # positivo = stai esportando
        batteria_prima = False
        soc_bat = None
        if self.balance_battery_soc_sensor:
            st_soc = self.hass.states.get(self.balance_battery_soc_sensor)
            if st_soc is not None and st_soc.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                soc_bat = _f(st_soc.state)
        priorita = self._setting_num("battery_priority", self.battery_priority_min)
        if soc_bat is not None and soc_bat < priorita:
            batteria_prima = True  # la batteria di casa deve caricarsi PRIMA dell'auto
        if self.balance_include_battery and self.balance_battery_sensor and not batteria_prima:
            st_bat = self.hass.states.get(self.balance_battery_sensor)
            if st_bat is not None and st_bat.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                # "Batteria solo senza sole" (switch): di giorno, col sole, l'auto va a SOLARE PURO.
                # La scarica batteria entra nel surplus solo quando la rete sta IMPORTANDO.
                if not self._switch_on("battery_night_only") or grid_w > 0:
                    surplus += _f(st_bat.state)  # scarica batteria >0 aggiunge al surplus

        amps_att = _num(self.hass, max_entity, 16.0)
        amps_min = self._setting_num("balance_min_amps", DEFAULT_MIN_AMPS)
        amps_max = self._setting_num("balance_max_amps", DEFAULT_MAX_AMPS)

        # deadband 100 W per evitare oscillazioni
        correzione = round(surplus / self.balance_wpa) if abs(surplus) > 100 else 0
        nuovi = min(max(amps_att + correzione, amps_min), amps_max)
        nuovi = float(round(nuovi))

        self.store.data.setdefault("counters", {})["balance_last"] = {
            "surplus_w": round(surplus), "ampere": nuovi,
            "rete_w": round(grid_w), "ts": datetime.now().strftime("%H:%M:%S"),
            "batteria_prima": batteria_prima, "soc_batteria": soc_bat,
        }
        if nuovi == amps_att:
            return

        try:
            await self.hass.services.async_call(
                "number", "set_value",
                {"entity_id": max_entity, "value": nuovi}, blocking=False,
            )
            self._balance_last_change = now_t
            _LOGGER.info("Bilanciamento solare: %s A → %s A (surplus %s W)",
                         amps_att, nuovi, round(surplus))
            if self._switch_on("notify_start"):
                await self._send_notify(
                    "☀️ Bilanciamento solare",
                    f"Rete: {round(grid_w)} W · Surplus: {round(surplus)} W\n"
                    f"Ampere: {amps_att} A → {nuovi} A",
                )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Bilanciamento: impostazione ampere fallita: %s", err)

    async def _home_balance(self, wb_state: str) -> None:
        """Bilanciamento casalingo: abbassa la wallbox se il consumo casa sale troppo.

        Soglie derivate dal contatore dichiarato: alta = potenza contatore,
        bassa = 80%. Isteresi temporale: 10 min sopra → ampere ridotti,
        15 min sotto → ampere ripristinati. Adattato dalle automazioni utente.
        """
        if not self._switch_on("home_balance") or not self.home_power_sensor:
            return
        if wb_state not in WALLBOX_CHARGING_STATES:
            self._home_hi_since = self._home_lo_since = None
            return
        max_entity = self.opts.get(CONF_WB_MAX_CURRENT)
        if not max_entity:
            return
        st = self.hass.states.get(self.home_power_sensor)
        if st is None or st.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        w = _f(st.state)
        unit = str(st.attributes.get("unit_of_measurement") or "").lower()
        if unit.startswith("kw"):  # sensore in kW → W
            w *= 1000.0
        hi = self.home_meter_kw * 1000.0
        lo = hi * 0.8
        now_t = time.time()
        self._home_last = {"w": round(w), "hi": round(hi), "lo": round(lo)}
        if w > hi:
            self._home_lo_since = None
            if self._home_hi_since is None:
                self._home_hi_since = now_t
            elif now_t - self._home_hi_since >= 600:
                self._home_hi_since = None
                await self._set_wb_amps(
                    max_entity, self.home_reduce_amps,
                    f"consumo casa {round(w)} W > {round(hi)} W per 10 min")
        elif w < lo:
            self._home_hi_since = None
            if self._home_lo_since is None:
                self._home_lo_since = now_t
            elif now_t - self._home_lo_since >= 900:
                self._home_lo_since = None
                await self._set_wb_amps(
                    max_entity, self.home_max_amps,
                    f"consumo casa {round(w)} W < {round(lo)} W per 15 min")
        else:
            self._home_hi_since = self._home_lo_since = None

    async def _set_wb_amps(self, entity: str, amps: float, motivo: str) -> None:
        """Imposta la corrente wallbox solo se diversa (tolleranza 0.5 A)."""
        cur = _num(self.hass, entity, None)
        if cur is not None and abs(cur - amps) < 0.5:
            return
        try:
            await self.hass.services.async_call(
                "number", "set_value", {"entity_id": entity, "value": amps},
                blocking=False,
            )
            _LOGGER.info("Bilanciamento casa: wallbox a %s A (%s)", amps, motivo)
            await self._send_notify(
                "🏠 Bilanciamento casa",
                f"Wallbox: {cur} A → {amps} A\n{motivo}",
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Bilanciamento casa: impostazione fallita: %s", err)

    async def _handle_charge_events(self, events: dict[str, Any], data: dict[str, Any],
                                    now) -> None:
        """Notifiche avvio/fine ricarica + promemoria + carica programmata."""
        # --- avvio / fine ricarica ------------------------------------------------
        if events.get("charge_started") and self._switch_on("notify_start"):
            zona = data.get("tipo_ricarica", "")
            await self._send_notify(
                "⚡ Ricarica avviata",
                f"La {data.get('capacity', 60):.0f}-kWh si sta caricando.\n"
                f"Tipo: {zona}\nBatteria: {data.get('battery')}%"
            )
        # NOTA: la notifica di FINE ricarica la manda l'automazione "Ricarica completata"
        # (visibile e attivabile dalla vista Automazioni, con posizione inclusa).
        # Qui NON la inviamo più: prima arrivavano DUE notifiche identiche.
        if events.get("charge_finished"):
            _LOGGER.info("Ricarica completata: %s kWh (notifica via automazione)",
                         events["charge_finished"].get("kwh"))

        # --- promemoria batteria bassa a casa --------------------------------------
        soglia = self._setting_num("low_soc", self.low_soc_threshold)
        inizio = self._setting_time("low_soc_start", self.low_soc_start)
        fine = self._setting_time("low_soc_end", self.low_soc_end)
        if self._switch_on("low_soc") and not data.get("charging"):
            hhmm = now.strftime("%H:%M")
            dentro = inizio <= hhmm <= fine if inizio <= fine else (hhmm >= inizio or hhmm <= fine)
            counters = self.store.data["counters"]
            today_key = now.strftime("%Y-%m-%d")
            if (dentro and WEEKDAYS[now.weekday()] in self.low_soc_days
                    and (data.get("location") or "") == "home"
                    and data.get("battery", 100) <= soglia
                    and counters.get("last_low_notify") != today_key):
                await self._send_notify(
                    "⚠️ Batteria bassa",
                    f"Batteria al {data.get('battery')}% ({data.get('range')} km).\n"
                    "Collega la wallbox!"
                )
                counters["last_low_notify"] = today_key
                self.persist(force=True)

        # --- carica programmata (orario o percentuale) ------------------------------
        if not (self.charge_sched_enabled and self._switch_on("charge_sched")):
            return
        if not self.charge_start_button:
            return
        charging = bool(data.get("charging"))
        battery = data.get("battery", 100.0)
        hhmm = now.strftime("%H:%M")
        today_key = now.strftime("%Y-%m-%d")

        mode = self._setting_opt("charge_sched_mode", self.charge_sched_mode)
        # SoC/orari di stop: quelli dell'AUTOMAZIONE salvata (vista Automazioni) hanno
        # priorità sui default del wizard — altrimenti l'orario scelto dall'utente si perdeva.
        _sc_prog = (self.store.data.get("schedule", {}) or {}).get("ricarica") or {}
        avvio_ora_s = str(_sc_prog.get("inizio") or "") or self._setting_time("charge_start_time", self.charge_start_time)
        stop_ora_s = str(_sc_prog.get("fine") or "") or self._setting_time("charge_stop_time", self.charge_stop_time)
        avvio_soc = self._setting_num("charge_start_soc", self.charge_start_soc)
        stop_soc = self._setting_num("charge_stop_soc", self.charge_stop_soc)
        stop_target = _f(_sc_prog.get("soc"), 0.0) or stop_soc

        if mode == "orario":
            in_window = _in_window(hhmm, avvio_ora_s, stop_ora_s)
            # avvio: all'interno della finestra, una volta al giorno
            if not charging and in_window and self._sched_done_key != f"start_{today_key}":
                await self._wb_charge(True, battery)
                self._sched_done_key = f"start_{today_key}"
            # stop: fuori dalla finestra OPPURE SoC obiettivo raggiunto
            # (prima il SoC veniva ignorato: la carica proseguiva oltre il 70%)
            if charging and (not in_window or battery >= stop_target):
                await self._wb_charge(False, battery)
        else:  # percentuale
            if not charging and battery <= avvio_soc:
                await self._wb_charge(True, battery)
            if charging and battery >= min(stop_soc, stop_target):
                await self._wb_charge(False, battery)

    async def _press_start(self) -> None:
        try:
            await self.hass.services.async_call(
                "button", "press", {"entity_id": self.charge_start_button}, blocking=False,
            )
            _LOGGER.info("Carica programmata: avvio inviato")
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Avvio carica programmata fallito: %s", err)

    async def _set_target_stop(self, battery: float) -> None:
        """Ferma la carica portando il target al SoC attuale."""
        if not self.charge_target_number:
            return
        try:
            await self.hass.services.async_call(
                "number", "set_value",
                {"entity_id": self.charge_target_number, "value": max(int(battery), 0)},
                blocking=False,
            )
            _LOGGER.info("Carica programmata: target impostato a %s%%", int(battery))
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Stop carica programmata fallito: %s", err)

    async def service_refresh_car(self) -> list[str]:
        """Forza la rilettura dal cloud Renault (posizione, odometro, batteria, autonomia…).

        Utile quando la posizione/lo stato restano indietro: chiede a HA di aggiornare
        le entità dell'auto (l'integrazione Renault ufficiale rifà il poll dal cloud).
        """
        ents = [
            self.opts.get(CONF_ODOMETER), self.opts.get(CONF_BATTERY_LEVEL),
            self.opts.get(CONF_RANGE), self.opts.get(CONF_CHARGING_ENTITY),
            self.opts.get(CONF_PLUG_ENTITY), self.opts.get(CONF_LOCATION_ENTITY),
        ]
        ents = [e for e in ents if e and self.hass.states.get(e) is not None]
        if not ents:
            return []
        try:
            await self.hass.services.async_call(
                "homeassistant", "update_entity", {"entity_id": ents}, blocking=False)
            _LOGGER.info("Aggiornamento auto forzato: %s", ", ".join(ents))
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Aggiornamento auto forzato fallito: %s", err)
        return ents

    async def service_export_csv(self) -> str:
        """Esporta viaggi e ricariche in CSV dentro config/renault_ev_center_export."""
        base = self.hass.config.path("renault_ev_center_export")
        os.makedirs(base, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        trips_path = os.path.join(base, f"{self.entry.entry_id[:8]}_trips_{stamp}.csv")

        def _write() -> str:
            fields = ["id", "data", "ora_inizio", "ora_fine", "durata_min", "km",
                      "mileage_inizio", "mileage_fine", "batteria_inizio", "batteria_fine",
                      "batteria_delta", "kwh_consumati", "kwh_per_100km",
                      "zona_partenza", "zona_arrivo"]
            with open(trips_path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                for row in self.store.data["trips"]:
                    writer.writerow(row)
            return trips_path

        return await self.hass.async_add_executor_job(_write)
