"""Coordinator Renault EV Center: legge le entità sorgente e gestisce motori e contatori."""
from __future__ import annotations

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
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CHARGE_STATE_ON_VALUES,
    CONF_BATTERY_LEVEL,
    CONF_BOLLO_EV,
    CONF_BOLLO_TERMICO,
    CONF_CAPACITY,
    CONF_CHARGING_EFFICIENCY,
    CONF_CHARGING_ENTITY,
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
    CONF_NAME,
    CONF_NOTIFY_DAYS,
    CONF_NOTIFY_SERVICE,
    CONF_ODOMETER,
    CONF_NOTIFY_CHARGE_START,
    CONF_NOTIFY_CHARGE_END,
    CONF_LOW_SOC_THRESHOLD,
    CONF_LOW_SOC_START,
    CONF_LOW_SOC_END,
    CONF_CHARGE_SCHED_ENABLED,
    CONF_CHARGE_SCHED_MODE,
    CONF_CHARGE_START_TIME,
    CONF_CHARGE_STOP_TIME,
    CONF_CHARGE_START_SOC,
    CONF_CHARGE_STOP_SOC,
    CONF_CHARGE_START_BUTTON,
    CONF_CHARGE_TARGET_NUMBER,
    CONF_WB_CHARGE_SWITCH,
    CONF_BALANCE_GRID_SENSOR,
    CONF_BALANCE_BATTERY_SENSOR,
    CONF_BALANCE_INVERT_GRID,
    CONF_BALANCE_INCLUDE_BATTERY,
    CONF_BALANCE_BATTERY_SOC_SENSOR,
    CONF_BATTERY_PRIORITY_MIN,
    CONF_BALANCE_WPA,
    DEFAULT_MAX_AMPS,
    DEFAULT_MIN_AMPS,
    DEFAULT_BATTERY_PRIORITY,
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
    CONF_TAGLIANDO_DATA,
    CONF_TAGLIANDO_INTERVALLO,
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


def _in_window(hhmm: str, start: str, stop: str) -> bool:
    if start <= stop:
        return start <= hhmm < stop
    return hhmm >= start or hhmm < stop


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
        self.temp_entity = opts.get(CONF_TEMP_ENTITY) or ""
        self.co2_enabled = bool(opts.get(CONF_CO2_ENABLED))
        self.co2_thermal_gkm = _f(opts.get(CONF_CO2_THERMAL_GKM), 120.0)
        self.co2_grid_gkwh = _f(opts.get(CONF_CO2_GRID_GKWH), 300.0)
        self.scadenze_enabled = bool(opts.get(CONF_SCADENZE_ENABLED))
        self.scad_bollo = str(opts.get(CONF_SCAD_BOLLO) or "")
        self.scad_revisione = str(opts.get(CONF_SCAD_REVISIONE) or "")
        self.scad_assicurazione = str(opts.get(CONF_SCAD_ASSICURAZIONE) or "")
        self.notify_service = str(opts.get(CONF_NOTIFY_SERVICE) or "")
        self.notify_days = int(_f(opts.get(CONF_NOTIFY_DAYS), 30))
        self.tagliando_mode = str(opts.get(CONF_TAGLIANDO_MODE) or "km")
        self.tagliando_data = str(opts.get(CONF_TAGLIANDO_DATA) or "")
        self.assicurazione_costo = _f(opts.get(CONF_ASSICURAZIONE_COSTO), 400.0)

        # vampire drain: SoC persa da fermo (non in carica, odometro fermo)
        self.drain_meter = DeltaMeter("down")
        self._drain_odom_ref: float | None = None

        # notifiche / automazioni ricarica
        self.notify_charge_start = bool(opts.get(CONF_NOTIFY_CHARGE_START, True))
        self.notify_charge_end = bool(opts.get(CONF_NOTIFY_CHARGE_END, True))
        self.low_soc_threshold = _f(opts.get(CONF_LOW_SOC_THRESHOLD), 25.0)
        self.low_soc_start = str(opts.get(CONF_LOW_SOC_START) or "18:00")
        self.low_soc_end = str(opts.get(CONF_LOW_SOC_END) or "22:00")
        self.charge_sched_enabled = bool(opts.get(CONF_CHARGE_SCHED_ENABLED, False))
        self.charge_sched_mode = str(opts.get(CONF_CHARGE_SCHED_MODE) or "orario")
        self.charge_start_time = str(opts.get(CONF_CHARGE_START_TIME) or "23:30")
        self.charge_stop_time = str(opts.get(CONF_CHARGE_STOP_TIME) or "07:00")
        self.charge_start_soc = _f(opts.get(CONF_CHARGE_START_SOC), 30.0)
        self.charge_stop_soc = _f(opts.get(CONF_CHARGE_STOP_SOC), 80.0)
        self.charge_start_button = opts.get(CONF_WB_CHARGE_SWITCH) or ""
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
        )

        # --- stato sessione di ricarica ------------------------------------------
        self.charge_session: dict[str, Any] | None = None
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
            self.wb_meters[p] = DeltaMeter.from_dict(counters.get(f"wb_{p}"))
            cm = counters.get(f"cost_{p}")
            m = _new_cost_meter()
            if isinstance(cm, dict):
                m.update({k: cm.get(k, v) for k, v in m.items()})
            self.cost_meters[p] = m
            self.kwh_meters[p] = {
                "up": DeltaMeter.from_dict(counters.get(f"kwh_{p}_up")),
                "down": DeltaMeter.from_dict(counters.get(f"kwh_{p}_down")),
            }
        self.pct_daily = {
            "up": DeltaMeter.from_dict(counters.get("pct_up")),
            "down": DeltaMeter.from_dict(counters.get("pct_down")),
        }
        self.drain_meter = DeltaMeter.from_dict(counters.get("drain_down"))
        self.cost_total = _f(counters.get("cost_total"), 0.0)
        if isinstance(counters.get("trip"), dict):
            self.trip.restore(counters["trip"])
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
            self.store.data["counters"] = c
            await self.store._store.async_save(c | {"trips": self.store.data["trips"][-2000:], "charges": self.store.data["charges"][-2000:], "daily": self.store.data["daily"][-365:], "health": self.store.data.get("health", {}), "maintenance": self.store.data.get("maintenance", [])[-200:], "monthly_km": self.store.data.get("monthly_km", {}), "scadenze": self.store.data.get("scadenze", {})})
        except Exception:  # noqa: BLE001
            pass

    def persist(self, force: bool = False) -> None:
        now = time.time()
        if not force and (now - self._last_save) < 300:
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
        self.store.data["counters"] = c
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
        self.trip.capacity_kwh = self.capacity

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
        """Prezzo carburante: sensore live se configurato, altrimenti valore fisso."""
        if self.diesel_price_entity:
            st = self.hass.states.get(self.diesel_price_entity)
            if st is not None and st.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                v = _f(st.state, 0.0)
                if v > 0.2:
                    return v
        return self.fuel_price

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
            return await self._async_update_data_inner()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Update fallito, uso dati precedenti: %s", err, exc_info=True)
            if self.data:
                return self.data
            raise

    async def _async_update_data_inner(self) -> dict[str, Any]:
        from homeassistant.helpers.update_coordinator import UpdateFailed as _UpdateFailed  # noqa: F401

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
                allow=wb_enabled and wb_state in WALLBOX_CHARGING_STATES,
                max_delta=30.0,
            )
            self.kwh_meters[p]["up"].tick(keys[p], avail_kwh, allow=True, max_delta=self.capacity * 0.35)
            self.kwh_meters[p]["down"].tick(keys[p], avail_kwh, allow=True, max_delta=self.capacity * 0.35)
        self.pct_daily["up"].tick(keys["daily"], battery if 0 <= battery <= 100 else None,
                                  allow=True, max_delta=25.0)
        self.pct_daily["down"].tick(keys["daily"], battery if 0 <= battery <= 100 else None,
                                    allow=True, max_delta=25.0)

        # --- temperatura esterna (opzionale) --------------------------------------
        temp_out = _num(hass, self.temp_entity, 0.0) if self.temp_entity else None

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
            if charging_wb and wb_delta > 0:
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

        # --- viaggi --------------------------------------------------------------
        now_wall = now.timestamp()
        now_mono = __import__("time").monotonic()
        trip_opened = False
        closed_trip = None
        opened, _ = self.trip.tick(odometer, battery, location, eff_kwh_100, now_wall, now_mono)
        trip_opened = opened
        if self.trip.should_close(now_mono):
            closed_trip = self.trip.close(location, eff_kwh_100, now_wall)
            if closed_trip is not None:
                self._enrich_trip(closed_trip)
                self.store.data["trips"].append(closed_trip)

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
                    closed_trip = chiuso_verifica
            if self.charge_session is None:
                self.charge_session = {
                    "id": int(time.time()),
                    "start_ts": time.time(),
                    "zone": location or "unknown",
                    "soc_start": battery,
                    "counter_start": self._wb_counter(),
                    "odometro_inizio": odometer,
                    "prezzo": self._price_for_zone(location or "home"),
                }
                started_charge = True
            self.charge_session["soc_now"] = battery
            self.charge_session["power_kw"] = wb_power
            if (time.time() - self.charge_session["start_ts"]) > 26 * 3600:
                finished_charge = self._finalize_charge(location, battery)
        elif self.charge_session is not None:
            self._charge_off_polls += 1
            if self._charge_off_polls >= 2:
                finished_charge = self._finalize_charge(location, battery)

        # --- storico giornaliero ---------------------------------------------------
        history = self.store.data["daily"]
        today_key = keys["daily"]
        if not self.today_rec or self.today_rec.get("data") != today_key:
            if self.today_rec.get("data"):
                prev = dict(self.today_rec)
                km_prev = _f(prev.get("km"))
                if km_prev >= 0.5:
                    prev["eff"] = round(_f(prev.get("kwh")) / km_prev * 100, 2) if km_prev else 0.0
                    history.append(prev)
                history.sort(key=lambda d: d.get("data", ""))
                del history[:-365]
            self.today_rec = {"data": today_key, "km": 0.0, "kwh": 0.0, "pct": 0.0, "eff": 0.0}
        km_oggi = _f(self.km_meters["daily"].value)
        kwh_oggi = _f(self.kwh_meters["daily"]["down"].value)
        self.today_rec.update({
            "km": round(km_oggi, 1),
            "kwh": round(kwh_oggi, 2),
            "pct": round(_f(self.pct_daily["down"].value), 1),
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
        target = self.target_soc
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
        savings: dict[str, Any] = {}
        if self.fuel_enabled:
            litri_100 = self.fuel_consumption
            prezzo_l = self._prezzo_termico()
            km_tot = odometer
            costo_termica_tot = km_tot * litri_100 * prezzo_l / 100.0
            costo_elettrico_tot = round(self.cost_total, 2)
            savings["totale"] = round(costo_termica_tot - costo_elettrico_tot, 2)
            savings["termica_totale"] = round(costo_termica_tot, 2)
            savings["elettrico_totale"] = costo_elettrico_tot
            savings["prezzo_termico"] = prezzo_l
            for label, period in (("mese", "monthly"), ("anno", "yearly")):
                km_p = _f(self.km_meters[period].value)
                costo_termica = km_p * litri_100 * prezzo_l / 100.0
                costo_elet = _f(self.cost_meters[period]["value"])
                savings[label] = round(costo_termica - costo_elet, 2)
            if self.maint_enabled:
                # anni di uso stimati sul chilometraggio (media 15.000 km/anno)
                anni = max(km_tot / 15000.0, 0.1)
                # Quanti tagliandi AVEREBBE FATTO l'auto termica in questi km
                tagliandi_termici = int(km_tot // self.tagliando_intervallo)
                spesa_termica_teoria = tagliandi_termici * self.tag_termico
                # Quanto HAI SPESO DAVVERO per l'elettrica (registro tagliandi)
                spesa_ev_reale = round(
                    sum(_f(m.get("costo")) for m in self.store.data.get("maintenance", [])), 2
                )
                risp_tagliandi = spesa_termica_teoria - spesa_ev_reale
                risp_bollo = anni * (self.bollo_termico - self.bollo_ev)
                savings["tagliandi"] = round(risp_tagliandi, 2)
                savings["tagliandi_teoria"] = round(spesa_termica_teoria, 2)
                savings["tagliandi_reale"] = spesa_ev_reale
                savings["tagliandi_n"] = tagliandi_termici
                savings["bollo"] = round(risp_bollo, 2)
                savings["netto"] = round(
                    _f(savings.get("totale")) + risp_tagliandi + risp_bollo, 2
                )

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
            co2 = {
                "totale": round(co2_termica - co2_ev, 1),
                "termica": round(co2_termica, 1),
                "ev": round(co2_ev, 1),
                "anno": round(
                    _f(self.km_meters["yearly"].value) * self.co2_thermal_gkm / 1000.0
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

            # tagliando: modalità km o data
            t_mode = scad_cfg.get("tagliando_mode", "km")
            km_anno = max(_f(self.km_meters["yearly"].value), 1.0)
            km_giorno = km_anno / 365.0
            if t_mode == "data" and scad_cfg.get("tagliando_data"):
                try:
                    t_data = _date.fromisoformat(str(scad_cfg["tagliando_data"]))
                    scadenze.append({"nome": "Tagliando", "data": t_data.isoformat(),
                                     "giorni": max((t_data - oggi_d).days, 0)})
                except ValueError:
                    pass
            else:
                ultimo_tag_km = max((_f(m.get("km")) for m in manutenzioni), default=0.0)
                target_km = _f(scad_cfg.get("tagliando_km"), ultimo_tag_km + self.tagliando_intervallo)
                mancanti = target_km - odometer
                scadenze.append({"nome": "Tagliando", "km": round(mancanti, 0),
                                 "data": f"{target_km:.0f} km",
                                 "giorni": max(int(mancanti / km_giorno), 0)})
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

        percorrenza = [
            {"nome": "Oggi", "pct": round(_f(self.pct_daily["down"].value), 1),
             "usati": round(_f(self.kwh_meters["daily"]["down"].value), 2),
             "caricati": round(_f(self.wb_meters["daily"].value), 2),
             "km": round(_f(self.km_meters["daily"].value), 0)},
            {"nome": "Ieri", "pct": round(_f(self.pct_daily["down"].last), 1),
             "usati": round(_f(self.kwh_meters["daily"]["down"].last), 2),
             "caricati": round(_f(self.wb_meters["daily"].last), 2),
             "km": round(_f(self.km_meters["daily"].last), 0)},
            {"nome": "Settimana", "usati": round(_f(self.kwh_meters["weekly"]["down"].value), 2),
             "caricati": round(_f(self.wb_meters["weekly"].value), 2),
             "km": round(_f(self.km_meters["weekly"].value), 0)},
            {"nome": "Settimana prec.", "usati": round(_f(self.kwh_meters["weekly"]["down"].last), 2),
             "caricati": round(_f(self.wb_meters["weekly"].last), 2),
             "km": round(_f(self.km_meters["weekly"].last), 0)},
            {"nome": "Mese", "usati": round(_f(self.kwh_meters["monthly"]["down"].value), 2),
             "caricati": round(_f(self.wb_meters["monthly"].value), 2),
             "km": round(_f(self.km_meters["monthly"].value), 0)},
            {"nome": "Mese prec.", "usati": round(_f(self.kwh_meters["monthly"]["down"].last), 2),
             "caricati": round(_f(self.wb_meters["monthly"].last), 2),
             "km": round(_f(self.km_meters["monthly"].last), 0)},
            {"nome": "Anno", "usati": round(_f(self.kwh_meters["yearly"]["down"].value), 2),
             "caricati": round(_f(self.wb_meters["yearly"].value), 2),
             "km": round(_f(self.km_meters["yearly"].value), 0)},
            {"nome": "Anno prec.", "usati": round(_f(self.kwh_meters["yearly"]["down"].last), 2),
             "caricati": round(_f(self.wb_meters["yearly"].last), 2),
             "km": round(_f(self.km_meters["yearly"].last), 0)},
        ]

        charges_filtered = self._filter_charges(charges, now)
        report = self._build_report(now, keys, today_key)

        data: dict[str, Any] = {
            "available": sources_ok,
            "odometer": round(odometer, 1),
            "battery": round(battery, 1),
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
            "wb_energy": {p: self.wb_meters[p].to_dict() for p in PERIODS},
            "cost": {p: dict(self.cost_meters[p]) for p in PERIODS},
            "cost_total": round(self.cost_total, 2),
            "pct_daily": {k: v.to_dict() for k, v in self.pct_daily.items()},
            "kwh_batt": {
                p: {d: self.kwh_meters[p][d].to_dict() for d in ("up", "down")}
                for p in PERIODS
            },
            "wb_power_kw": round(wb_power, 2),
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
                "ts_inizio": datetime.fromtimestamp(self.trip.ts_start).isoformat()
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
            "history_days": history[-365:],
            "trips_oggi": len(trips_oggi_list),
            "km_oggi_trip": round(sum(_f(t.get("km")) for t in trips_oggi_list), 1),
            "charges_oggi": len(charges_oggi),
            "charges_mese": len(charges_mese),
            "last_charge": charges[-1] if charges else None,
            "savings": savings,
            "health": dict(self.store.data.get("health", {})),
            "charges_filtered": charges_filtered,
            "report": report,
            "temp_out": temp_out,
            "drain_oggi_pct": round(self.drain_meter.value, 1),
            "drain_oggi_kwh": round(self.drain_meter.value * kwh_per_1pct, 2),
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
        await self._handle_charge_events(data["events"], data, now)
        await self._balance_solar(data, wb_state)
        data["balance"] = dict(self.store.data.get("counters", {}).get("balance_last", {}))
        return data

    # ------------------------------------------------------------ fine ricarica
    def _finalize_charge(self, zone: str, battery: float) -> dict[str, Any]:
        s = self.charge_session
        assert s is not None
        durata_min = int((time.time() - s["start_ts"]) / 60)
        counter_end = self._wb_counter()
        kwh = 0.0
        if s.get("counter_start") is not None and counter_end is not None:
            kwh = max(counter_end - s["counter_start"], 0.0)
        if kwh <= 0:
            soc_gain = max(battery - s["soc_start"], 0.0)
            kwh = soc_gain * self.capacity / 100.0
        z = (s.get("zone") or zone or "unknown").lower()
        if z == "home":
            tipo = "Casa"
        elif self.solar_zone and z == self.solar_zone:
            tipo = "Fotovoltaico"
        else:
            tipo = "Pubblica"
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
            "costo": costo,
            "tipo": tipo,
        }

        # --- salute batteria (solo ricariche a casa misurate dalla wallbox) -------
        delta_pct = battery - _f(s.get("soc_start"))
        wb_misurato = s.get("counter_start") is not None and counter_end is not None and kwh > 0
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
            if delta_pct > 5:
                health["soh_stimato"] = round(
                    (kwh * 0.92 / delta_pct) * (100.0 / self.capacity) * 100.0, 1
                )
            sessions = health.setdefault("sessions", [])
            sessions.append({
                "id": record["id"], "data": record["data"], "eff": eff,
                "perdite_kwh": perdite, "delta_pct": round(delta_pct, 1), "kwh": record["kwh"],
            })
            del sessions[:-100]

        self.store.data["charges"].append(record)
        self.charge_session = None
        self._charge_off_polls = 0
        self.persist(force=True)
        return record

    # ------------------------------------------------------------- arricchimenti
    def _enrich_trip(self, record: dict[str, Any]) -> None:
        """Costo stimato, fonte ultima ricarica e DOPPIA VERIFICA con il GPS."""
        record["costo_stimato"] = round(_f(record.get("kwh_consumati")) * self.price_home, 2)
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

    def _filter_charges(self, charges: list[dict], now) -> dict[str, Any]:
        """Filtra le ricariche secondo i select tipo/periodo/anno e calcola i totali."""
        tipo = self._setting_opt("filtro_tipo", "Tutte")
        periodo = self._setting_opt("filtro_periodo", "Mese")
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
        items = []
        for c in charges:
            if tipo != "Tutte" and c.get("tipo") != tipo:
                continue
            if anno != "Tutti" and str(c.get("data", ""))[:4] != anno:
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
                                  quando: datetime | None) -> dict[str, Any]:
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
        }
        self.store.data["charges"].append(record)
        self.cost_total += record["costo"]
        self.persist(force=True)
        return record

    def service_delete_trip(self, trip_id: int) -> bool:
        prima = len(self.store.data["trips"])
        self.store.data["trips"] = [t for t in self.store.data["trips"] if t.get("id") != trip_id]
        self.persist(force=True)
        return len(self.store.data["trips"]) < prima

    def service_add_maintenance(self, data: str, km: float, costo: float,
                                tipo: str, note: str = "") -> dict[str, Any]:
        """Registra un tagliando/Manutenzione effettuato."""
        record = {
            "id": int(time.time()),
            "data": data,
            "km": round(km, 0),
            "costo": round(costo, 2),
            "tipo": tipo or "Tagliando",
            "note": note or "",
        }
        self.store.data.setdefault("maintenance", []).append(record)
        self.store.data["maintenance"].sort(key=lambda m: m.get("data", ""))
        self.persist(force=True)
        return record

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

    async def service_create_automations(self) -> list[str]:
        """Crea (o aggiorna) le 3 automazioni consigliate nello store di HA."""
        from homeassistant.helpers.storage import Store

        from .dashboard import slugify

        n = slugify(str(self.opts.get(CONF_NAME, "Renault")))
        batt = str(self.opts.get("battery_level_entity") or f"sensor.{n}_batteria")
        range_e = str(self.opts.get("range_entity") or f"sensor.{n}_autonomia_della_batteria")
        charging = str(self.opts.get("charging_entity") or f"binary_sensor.{n}_in_carica")
        loc = str(self.opts.get("location_entity") or "")
        notify = self.notify_service or "persistent_notification"
        target = notify if "." in notify else f"notify.{notify}"

        def _pn(notif_id: str, title: str, msg: str) -> dict:
            if target.startswith("notify."):
                return {"service": target, "data": {"title": title, "message": msg}}
            return {"service": "persistent_notification.create",
                    "data": {"notification_id": notif_id, "title": title, "message": msg}}

        autos: dict[str, dict] = {
            f"renault_ev_center_{n}_ricarica_completata": {
                "alias": f"Renault EV Center — Ricarica completata ({n})",
                "triggers": [{"trigger": "state", "entity_id": charging,
                              "from": "on", "to": "off", "for": {"minutes": 3}}],
                "conditions": [{"condition": "template",
                                "value_template": "{{ state_attr('sensor." + n + "_ultima_ricarica', 'data') == now().strftime('%Y-%m-%d') }}"}],
                "actions": [_pn(f"rec_ric_{n}", "🔋 Ricarica completata",
                                "⚡ {{ states('sensor." + n + "_ultima_ricarica') }} kWh · "
                                "🔋 {{ state_attr('sensor." + n + "_ultima_ricarica', 'soc_end') }}% · "
                                "💰 {{ state_attr('sensor." + n + "_ultima_ricarica', 'costo') }} €")],
                "mode": "single",
            },
            f"renault_ev_center_{n}_batteria_bassa": {
                "alias": f"Renault EV Center — Batteria bassa fuori casa ({n})",
                "triggers": [{"trigger": "numeric_state", "entity_id": batt, "below": 25}],
                "conditions": ([{"condition": "not", "conditions": [
                    {"condition": "state", "entity_id": loc, "state": "home"}]}] if loc else [])
                    + [{"condition": "time", "after": "07:00:00", "before": "22:00:00"}],
                "actions": [_pn(f"rec_low_{n}", "🚗 Batteria bassa",
                                "Batteria al {{ states('" + batt + "') }}% "
                                "({{ states('" + range_e + "') }} km). Ricorda di caricare!")],
                "mode": "single", "max_exceeded": "silent",
            },
            f"renault_ev_center_{n}_riassunto_giornaliero": {
                "alias": f"Renault EV Center — Riassunto giornaliero ({n})",
                "triggers": [{"trigger": "time", "at": "21:30:00"}],
                "conditions": [{"condition": "numeric_state",
                                "entity_id": f"sensor.{n}_km_giornalieri", "above": 0.5}],
                "actions": [_pn(f"rec_sum_{n}", "📊 Oggi con la tua Renault",
                                "🚗 {{ states('sensor." + n + "_km_giornalieri') }} km · "
                                "📈 {{ states('sensor." + n + "_kwh_per_100km') }} kWh/100km · "
                                "💸 {{ states('sensor." + n + "_costo_per_km') }} €/km")],
                "mode": "single",
            },
        }

        store = Store(self.hass, 1, "automation")
        items = await store.async_load() or {"items": {}}
        if not isinstance(items, dict) or not isinstance(items.get("items"), dict):
            items = {"items": {}}
        for aid, cfg in autos.items():
            items["items"][aid] = {"id": aid, "isolated": False, "config": cfg}
        await store.async_save(items)
        await self.hass.services.async_call("automation", "reload", {}, blocking=True)
        return list(autos)

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
        ent = self.charge_start_button  # ora contiene l'entità wallbox (switch/button)
        try:
            domain = ent.split(".")[0] if ent else ""
            if ent and domain == "switch":
                await self.hass.services.async_call(
                    "switch", "turn_on" if avvia else "turn_off",
                    {"entity_id": ent}, blocking=False,
                )
                _LOGGER.info("Carica programmata: wallbox %s", "avviata" if avvia else "fermata")
                return
            if ent and domain == "button":
                await self.hass.services.async_call(
                    "button", "press", {"entity_id": ent}, blocking=False,
                )
                _LOGGER.info("Carica programmata: pulsante wallbox premuto (%s)",
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
        finished = events.get("charge_finished")
        if finished and self._switch_on("notify_end"):
            await self._send_notify(
                "🔋 Ricarica completata",
                f"⚡ Energia: {finished.get('kwh')} kWh\n"
                f"🔋 Batteria: {finished.get('soc_start')}% → {finished.get('soc_end')}%\n"
                f"💰 Costo: {finished.get('costo')} €\n"
                f"🏷️ {finished.get('tipo')}"
            )

        # --- promemoria batteria bassa a casa --------------------------------------
        soglia = self._setting_num("low_soc", self.low_soc_threshold)
        inizio = self._setting_time("low_soc_start", self.low_soc_start)
        fine = self._setting_time("low_soc_end", self.low_soc_end)
        if self._switch_on("low_soc") and not data.get("charging"):
            hhmm = now.strftime("%H:%M")
            dentro = inizio <= hhmm <= fine if inizio <= fine else (hhmm >= inizio or hhmm <= fine)
            counters = self.store.data["counters"]
            today_key = now.strftime("%Y-%m-%d")
            if (dentro and (data.get("location") or "") == "home"
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
        avvio_ora_s = self._setting_time("charge_start_time", self.charge_start_time)
        stop_ora_s = self._setting_time("charge_stop_time", self.charge_stop_time)
        avvio_soc = self._setting_num("charge_start_soc", self.charge_start_soc)
        stop_soc = self._setting_num("charge_stop_soc", self.charge_stop_soc)

        if mode == "orario":
            in_window = _in_window(hhmm, avvio_ora_s, stop_ora_s)
            # avvio: all'interno della finestra, una volta al giorno
            if not charging and in_window and self._sched_done_key != f"start_{today_key}":
                await self._wb_charge(True, battery)
                self._sched_done_key = f"start_{today_key}"
            # stop: fuori dalla finestra
            if charging and not in_window:
                await self._wb_charge(False, battery)
        else:  # percentuale
            if not charging and battery <= avvio_soc:
                await self._wb_charge(True, battery)
            if charging and battery >= stop_soc:
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
