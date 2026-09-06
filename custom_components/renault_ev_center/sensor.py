"""Sensori Renault EV Center."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_WALLBOX_ENABLED, DOMAIN
from .coordinator import PERIODS, RenaultMateCoordinator

_LOGGER = logging.getLogger(__name__)

PERIOD_LABELS_IT = {
    "daily": ("Giornalieri", "Giornaliero", "giornaliero"),
    "weekly": ("Settimanali", "Settimanale", "settimanale"),
    "monthly": ("Mensili", "Mensile", "mensile"),
    "yearly": ("Annuali", "Annuale", "annuale"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RenaultMateCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = str(entry.data.get("name") or entry.title or "Auto")
    wb = bool(entry.options.get(CONF_WALLBOX_ENABLED, entry.data.get(CONF_WALLBOX_ENABLED, False)))

    entities: list[SensorEntity] = [
        EffKmPerKwh(coordinator, name),
        EffKwh100(coordinator, name),
        BatteryKwh(coordinator, name),
        KwhTotaliConsumati(coordinator, name),
        PercPer100km(coordinator, name),
        CostPerKm(coordinator, name),
        CostPer100Km(coordinator, name),
        TempoRicarica(coordinator, name),
        OraCompletamento(coordinator, name),
        CostoRicaricaCorrente(coordinator, name),
        TipoRicarica(coordinator, name),
        TripAttivoInfo(coordinator, name),
        TripKmCorrenti(coordinator, name),
        TripDurata(coordinator, name),
        UltimoTrip(coordinator, name),
        TripsOggi(coordinator, name),
        KmOggiTrip(coordinator, name),
        StatisticheViaggi(coordinator, name),
        ViaggiRecenti(coordinator, name),
        ArchivioViaggi(coordinator, name),
        StoricoGiornaliero(coordinator, name),
        ListaRicariche(coordinator, name),
        ReportGenerale(coordinator, name),
        UltimaRicarica(coordinator, name),
        RicaricheContatore(coordinator, name, "oggi"),
        RicaricheContatore(coordinator, name, "mese"),
        EfficienzaRicarica(coordinator, name),
        PerditeRicarica(coordinator, name),
        EnergiaBatteriaUltimaRicarica(coordinator, name),
        SohStimato(coordinator, name),
        KwhPer1Pct(coordinator, name),
        Tagliandi(coordinator, name),
        DrainFermo(coordinator, name),
        ConsumoZona(coordinator, name),
        CO2Risparmiata(coordinator, name),
        Scadenze(coordinator, name),
        ViaggioEstremo(coordinator, name),
        EnergiaCasaTotale(coordinator, name),
        Percorrenza(coordinator, name),
        Assicurazione(coordinator, name),
        FvMese(coordinator, name),
        FvTotale(coordinator, name),
    ]

    for p in PERIODS:
        label = PERIOD_LABELS_IT[p][0]
        entities.append(PeriodKmSensor(coordinator, name, p, label))
        entities.append(WbEnergySensor(coordinator, name, p))
    entities.append(WbEnergySensor(coordinator, name, "total"))

    for p in PERIODS:
        label = PERIOD_LABELS_IT[p][1]
        entities.append(CostoRicaricaSensor(coordinator, name, p, label))
    entities.append(CostoRicaricaSensor(coordinator, name, "total", "Totale"))

    entities.append(PctBatteriaOggi(coordinator, name, "up"))
    entities.append(PctBatteriaOggi(coordinator, name, "down"))
    for p in PERIODS:
        label = PERIOD_LABELS_IT[p][1]
        entities.append(EnergiaBatteriaSensor(coordinator, name, p, label))

    if coordinator.fuel_enabled:
        entities.append(RisparmioTermica(coordinator, name, "totale"))
        entities.append(RisparmioTermica(coordinator, name, "mese"))
        entities.append(RisparmioTermica(coordinator, name, "anno"))
        if coordinator.maint_enabled:
            entities.append(RisparmioExtra(coordinator, name, "tagliandi"))
            entities.append(RisparmioExtra(coordinator, name, "bollo"))
            entities.append(RisparmioExtra(coordinator, name, "netto"))

    if wb:
        entities.append(WbPotenza(coordinator, name))

    async_add_entities(entities)


class MateSensor(CoordinatorEntity[RenaultMateCoordinator], SensorEntity):
    """Base comune."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: RenaultMateCoordinator, name: str) -> None:
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._mate_name = name

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


# ------------------------------------------------------------------ efficienza
class EffKmPerKwh(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_eff_km_per_kwh"
        self._attr_name = f"{name} Km per kWh"
        self._attr_native_unit_of_measurement = "km/kWh"
        self._attr_icon = "mdi:speedometer"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data.get("eff_km_per_kwh")


class EffKwh100(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_eff_kwh_100km"
        self._attr_name = f"{name} kWh per 100km"
        self._attr_native_unit_of_measurement = "kWh/100km"
        self._attr_icon = "mdi:battery-charging-100"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data.get("eff_kwh_100km")


class BatteryKwh(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_battery_kwh"
        self._attr_name = f"{name} Batteria kWh Disponibili"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = SensorDeviceClass.ENERGY_STORAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data.get("battery_kwh")


class CostPerKm(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_cost_per_km"
        self._attr_name = f"{name} Costo per km"
        self._attr_native_unit_of_measurement = "€/km"
        self._attr_icon = "mdi:currency-eur"

    @property
    def native_value(self):
        km_per_kwh = self.coordinator.data.get("eff_km_per_kwh") or 0
        if km_per_kwh > 0:
            return round(self.coordinator.price_home / km_per_kwh, 3)
        return 0.0


class CostPer100Km(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_cost_per_100km"
        self._attr_name = f"{name} Costo per 100 km"
        self._attr_native_unit_of_measurement = "€/100km"
        self._attr_icon = "mdi:currency-eur"

    @property
    def native_value(self):
        kwh100 = self.coordinator.data.get("eff_kwh_100km") or 0
        return round(kwh100 * self.coordinator.price_home, 2)


# ------------------------------------------------------------------ contatori km
class PeriodKmSensor(MateSensor):
    def __init__(self, coordinator, name, period, label):
        super().__init__(coordinator, name)
        self._period = period
        self._attr_unique_id = f"{coordinator.entry.entry_id}_km_{period}"
        self._attr_name = f"{name} Km {label}"
        self._attr_native_unit_of_measurement = "km"
        self._attr_device_class = SensorDeviceClass.DISTANCE
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:map-marker-distance"

    @property
    def native_value(self):
        return round(self.coordinator.data["km"][self._period]["value"], 1)

    @property
    def extra_state_attributes(self):
        return {"last_period": self.coordinator.data["km"][self._period]["last"]}


# ------------------------------------------------------------- energia wallbox
class WbEnergySensor(MateSensor):
    def __init__(self, coordinator, name, period):
        super().__init__(coordinator, name)
        self._period = period
        labels = {
            "daily": "Energia Caricata Giornaliera",
            "weekly": "Energia Caricata Settimanale",
            "monthly": "Energia Caricata Mensile",
            "yearly": "Energia Caricata Annuale",
            "total": "Energia Caricata Totale",
        }
        self._attr_unique_id = f"{coordinator.entry.entry_id}_wb_energy_{period}"
        self._attr_name = f"{name} {labels[period]}"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:ev-station"

    @property
    def native_value(self):
        if self._period == "total":
            # totale = somma delle ricariche registrate
            return round(
                sum(float(c.get("kwh", 0)) for c in self.coordinator.store.data["charges"]),
                2,
            )
        return round(self.coordinator.data["wb_energy"][self._period]["value"], 2)

    @property
    def extra_state_attributes(self):
        if self._period == "total":
            return {}
        return {"last_period": self.coordinator.data["wb_energy"][self._period]["last"]}


class CostoRicaricaSensor(MateSensor):
    def __init__(self, coordinator, name, period, label):
        super().__init__(coordinator, name)
        self._period = period
        self._attr_unique_id = f"{coordinator.entry.entry_id}_cost_{period}"
        self._attr_name = f"{name} Costo Ricarica {label}"
        self._attr_native_unit_of_measurement = "€"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:currency-eur"

    @property
    def native_value(self):
        if self._period == "total":
            return round(self.coordinator.cost_total, 2)
        return round(float(self.coordinator.data["cost"][self._period]["value"]), 2)

    @property
    def extra_state_attributes(self):
        if self._period == "total":
            return {}
        return {"last_period": self.coordinator.data["cost"][self._period]["last"]}


# ------------------------------------------------------------ batteria carica/scarica
class PctBatteriaOggi(MateSensor):
    def __init__(self, coordinator, name, direction):
        super().__init__(coordinator, name)
        self._direction = direction
        label = "Caricata" if direction == "up" else "Scaricata"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_pct_oggi_{direction}"
        self._attr_name = f"{name} Batteria % {label} Oggi"
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:battery-charging" if direction == "up" else "mdi:battery-minus"

    @property
    def native_value(self):
        return round(abs(self.coordinator.data["pct_daily"][self._direction]["value"]), 1)

    @property
    def extra_state_attributes(self):
        return {
            "last_period": abs(self.coordinator.data["pct_daily"][self._direction]["last"])
        }


class EnergiaBatteriaSensor(MateSensor):
    def __init__(self, coordinator, name, period, label):
        super().__init__(coordinator, name)
        self._period = period
        self._attr_unique_id = f"{coordinator.entry.entry_id}_batt_energy_{period}"
        self._attr_name = f"{name} Energia Batteria {label}"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:battery-charging-outline"

    def _meter(self, direction):
        return self.coordinator.data["kwh_batt"][self._period][direction]

    @property
    def native_value(self):
        return round(abs(self._meter("down")["value"]), 2)

    @property
    def extra_state_attributes(self):
        return {
            "caricata": round(abs(self._meter("up")["value"]), 2),
            "caricata_last_period": round(abs(self._meter("up")["last"]), 2),
            "scaricata_last_period": round(abs(self._meter("down")["last"]), 2),
        }


# ---------------------------------------------------------------- stime ricarica
class TempoRicarica(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_tempo_ricarica"
        self._attr_name = f"{name} Tempo Ricarica Stimato"
        self._attr_icon = "mdi:clock-end"

    @property
    def native_value(self):
        est = self.coordinator.data["estimate"]
        return est["tempo"]

    @property
    def extra_state_attributes(self):
        est = self.coordinator.data["estimate"]
        return {
            "stato_ricarica": est["status"],
            "potenza_attuale": f'{self.coordinator.data["wb_power_kw"]} kW',
            "energia_rimanente": f'{est["kwh_needed"]} kWh',
        }


class OraCompletamento(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_ora_completamento"
        self._attr_name = f"{name} Ora Completamento Ricarica"
        self._attr_icon = "mdi:clock-time-four"

    @property
    def native_value(self):
        return self.coordinator.data["estimate"]["completion"]


class CostoRicaricaCorrente(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_costo_corrente"
        self._attr_name = f"{name} Costo Ricarica Corrente Stimato"
        self._attr_native_unit_of_measurement = "€"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_icon = "mdi:currency-eur"

    @property
    def native_value(self):
        return self.coordinator.data["estimate"]["costo_stimato"]


class TipoRicarica(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_tipo_ricarica"
        self._attr_name = f"{name} Tipo Ricarica Attuale"

    @property
    def native_value(self):
        return self.coordinator.data["tipo_ricarica"]

    @property
    def icon(self):
        valore = self.coordinator.data["tipo_ricarica"]
        if valore == "Ricarica a Casa":
            return "mdi:home-battery"
        if valore == "Ricarica Fotovoltaico":
            return "mdi:solar-power-variant"
        if valore == "Ricarica Pubblica":
            return "mdi:ev-station"
        return "mdi:battery-charging-outline"


# ------------------------------------------------------------------------ viaggi
class TripAttivoInfo(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_trip_attivo"
        self._attr_name = f"{name} Trip Attivo"

    @property
    def native_value(self):
        return "on" if self.coordinator.data["trip"]["active"] else "off"

    @property
    def icon(self):
        return "mdi:car-side" if self.coordinator.data["trip"]["active"] else "mdi:car"

    @property
    def extra_state_attributes(self):
        t = self.coordinator.data["trip"]
        return {
            "partenza": t["zona_partenza"],
            "km_percorsi": t["km"],
            "batteria_delta": t["battery_delta"],
            "durata_min": t["durata_min"],
            "ts_inizio": t["ts_inizio"],
        }


class TripKmCorrenti(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_trip_km"
        self._attr_name = f"{name} Km Trip Corrente"
        self._attr_native_unit_of_measurement = "km"
        self._attr_device_class = SensorDeviceClass.DISTANCE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:map-marker-distance"

    @property
    def native_value(self):
        return self.coordinator.data["trip"]["km"]


class TripDurata(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_trip_durata"
        self._attr_name = f"{name} Durata Trip Corrente"
        self._attr_native_unit_of_measurement = "min"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:timer-outline"

    @property
    def native_value(self):
        return self.coordinator.data["trip"]["durata_min"]


class UltimoTrip(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_ultimo_trip"
        self._attr_name = f"{name} Ultimo Trip"
        self._attr_native_unit_of_measurement = "km"
        self._attr_device_class = SensorDeviceClass.DISTANCE
        self._attr_icon = "mdi:flag-checkered"

    @property
    def native_value(self):
        ultimo = self.coordinator.data.get("last_trip")
        return float(ultimo["km"]) if ultimo else 0.0

    @property
    def extra_state_attributes(self):
        ultimo = self.coordinator.data.get("last_trip")
        if not ultimo:
            return {}
        return {
            "data": ultimo.get("data"),
            "ora_inizio": ultimo.get("ora_inizio"),
            "ora_fine": ultimo.get("ora_fine"),
            "durata_min": ultimo.get("durata_min"),
            "km": ultimo.get("km"),
            "batteria_inizio": ultimo.get("batteria_inizio"),
            "batteria_fine": ultimo.get("batteria_fine"),
            "batteria_delta": ultimo.get("batteria_delta"),
            "kwh_consumati": ultimo.get("kwh_consumati"),
            "kwh_per_100km": ultimo.get("kwh_per_100km"),
            "costo_stimato": ultimo.get("costo_stimato"),
            "carica_precedente": ultimo.get("carica_precedente"),
            "gps_arrivo": ultimo.get("gps_arrivo"),
            "verifica": ultimo.get("verifica"),
            "zona_partenza": ultimo.get("zona_partenza"),
            "zona_arrivo": ultimo.get("zona_arrivo"),
        }


class TripsOggi(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_trips_oggi"
        self._attr_name = f"{name} Trip Completati Oggi"
        self._attr_native_unit_of_measurement = "trip"
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:counter"

    @property
    def native_value(self):
        return self.coordinator.data["trips_oggi"]


class KmOggiTrip(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_km_oggi_trip"
        self._attr_name = f"{name} Km Oggi (Trip)"
        self._attr_native_unit_of_measurement = "km"
        self._attr_device_class = SensorDeviceClass.DISTANCE
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:map-marker-distance"

    @property
    def native_value(self):
        return self.coordinator.data["km_oggi_trip"]


class StatisticheViaggi(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_stat_viaggi"
        self._attr_name = f"{name} Statistiche Viaggi"
        self._attr_native_unit_of_measurement = "km"
        self._attr_device_class = SensorDeviceClass.DISTANCE
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:chart-bar"

    @property
    def native_value(self):
        return self.coordinator.data["stats_30d"]["km_totali"]

    @property
    def extra_state_attributes(self):
        d = self.coordinator.data
        return {
            "ultimi_7_giorni": d["stats_7d"],
            "ultimi_30_giorni": d["stats_30d"],
            "ultimi_90_giorni": d["stats_90d"],
            "totale_viaggi": d["stats_all"]["n_trip"],
            "km_totali": d["stats_all"]["km_totali"],
            "kwh_totali_viaggi": d["stats_all"]["kwh_totali"],
            "ore_guida_totali": round(d["stats_all"]["durata_totale_min"] / 60.0, 1),
            "migliore_efficienza": d.get("best_eff", 0.0),
            "efficienza_media": d["stats_all"]["kwh_per_100km"],
            "caricata_casa": d.get("charges_by_type", {}).get("Casa"),
            "caricata_fotovoltaico": d.get("charges_by_type", {}).get("Fotovoltaico"),
            "caricata_pubblica": d.get("charges_by_type", {}).get("Pubblica"),
        }


class ViaggiRecenti(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_viaggi_recenti"
        self._attr_name = f"{name} Viaggi Recenti"
        self._attr_native_unit_of_measurement = "trip"
        self._attr_icon = "mdi:format-list-bulleted"

    @property
    def native_value(self):
        return len(self.coordinator.data["trips_recent"])

    @property
    def extra_state_attributes(self):
        return {"trips": self.coordinator.data["trips_recent"]}


class StoricoGiornaliero(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_storico_giornaliero"
        self._attr_name = f"{name} Storico Giornaliero"
        self._attr_native_unit_of_measurement = "giorni"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self):
        return len(self.coordinator.data["history_days"])

    @property
    def extra_state_attributes(self):
        # storico completo 365 giorni per annuale
        return {"days": self.coordinator.data["history_days"]}


# --------------------------------------------------------------------- ricariche
class UltimaRicarica(MateSensor):
    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_ultima_ricarica"
        self._attr_name = f"{name} Ultima Ricarica"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self):
        ric = self.coordinator.data.get("last_charge")
        return float(ric["kwh"]) if ric else 0.0

    @property
    def extra_state_attributes(self):
        ric = self.coordinator.data.get("last_charge")
        if not ric:
            return {}
        return {
            "data": ric.get("data"),
            "ora_inizio": ric.get("ora_inizio"),
            "ora_fine": ric.get("ora_fine"),
            "durata_min": ric.get("durata_min"),
            "soc_start": ric.get("soc_start"),
            "soc_end": ric.get("soc_end"),
            "potenza_media_kw": ric.get("potenza_media_kw"),
            "costo": ric.get("costo"),
            "tipo": ric.get("tipo"),
        }


class RicaricheContatore(MateSensor):
    def __init__(self, coordinator, name, periodo):
        super().__init__(coordinator, name)
        self._periodo = periodo
        label = "Oggi" if periodo == "oggi" else "Mese"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_ricariche_{periodo}"
        self._attr_name = f"{name} Ricariche {label}"
        self._attr_native_unit_of_measurement = "ricariche"
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:counter"

    @property
    def native_value(self):
        key = "charges_oggi" if self._periodo == "oggi" else "charges_mese"
        return self.coordinator.data[key]


# ---------------------------------------------------------------------- risparmio
class RisparmioTermica(MateSensor):
    def __init__(self, coordinator, name, periodo):
        super().__init__(coordinator, name)
        self._periodo = periodo
        labels = {
            "totale": "Risparmio Totale vs",
            "mese": "Risparmio Mese vs",
            "anno": "Risparmio Anno vs",
        }
        self._attr_unique_id = f"{coordinator.entry.entry_id}_risparmio_{periodo}"
        self._attr_name = f"{labels[periodo]} {coordinator.fuel_label}"
        self._attr_native_unit_of_measurement = "€"
        self._attr_icon = "mdi:currency-eur-off"

    @property
    def native_value(self):
        savings = self.coordinator.data.get("savings", {})
        return savings.get(self._periodo, 0.0)

    @property
    def extra_state_attributes(self):
        savings = self.coordinator.data.get("savings", {})
        return {
            "termica_totale": savings.get("termica_totale"),
            "elettrico_totale": savings.get("elettrico_totale"),
            "prezzo_termico": savings.get("prezzo_termico"),
        }


# ------------------------------------------------------------------ wallbox potenza
class WbPotenza(MateSensor):
    """Potenza di carica normalizzata in kW (converte automaticamente i W)."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_wb_potenza"
        self._attr_name = f"{name} Wallbox Potenza"
        self._attr_native_unit_of_measurement = "kW"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:flash"

    @property
    def native_value(self):
        return self.coordinator.data.get("wb_power_kw")

    @property
    def extra_state_attributes(self):
        b = self.coordinator.data.get("balance", {})
        if not b:
            return {}
        return {
            "bilanciamento_ultimo_aggiustamento": b.get("ts"),
            "surplus_w": b.get("surplus_w"),
            "rete_w": b.get("rete_w"),
            "ampere_impostati": b.get("ampere"),
        }


# ------------------------------------------------------------- extra consumo
class KwhTotaliConsumati(MateSensor):
    """Stima dei kWh consumati in tutta la vita dell'auto (odometro / km-per-kWh)."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_kwh_totali"
        self._attr_name = f"{name} kWh Totali Consumati"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:battery-charging-high"

    @property
    def native_value(self):
        odometer = self.coordinator.data.get("odometer") or 0
        eff = self.coordinator.data.get("eff_km_per_kwh") or 0
        if eff > 0 and odometer > 0:
            return round(odometer / eff, 1)
        return 0.0


class PercPer100km(MateSensor):
    """Percentuale di batteria consumata per 100 km oggi."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_perc_per_100km"
        self._attr_name = f"{name} Batteria % per 100km"
        self._attr_native_unit_of_measurement = "%/100km"
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self):
        km = self.coordinator.data["km"]["daily"]["value"]
        perc = abs(self.coordinator.data["pct_daily"]["down"]["value"])
        if km > 0 and perc > 0:
            return round(perc / km * 100, 1)
        return 0.0


# ------------------------------------------------------- archivi / liste / report
class ArchivioViaggi(MateSensor):
    """Ultimi viaggi registrati (attributo 'trips' limitato)."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_archivio_viaggi"
        self._attr_name = f"{name} Archivio Viaggi"
        self._attr_native_unit_of_measurement = "trip"
        self._attr_icon = "mdi:archive"

    @property
    def native_value(self):
        return len(self.coordinator.store.data["trips"])

    @property
    def extra_state_attributes(self):
        trips = sorted(
            self.coordinator.store.data["trips"],
            key=lambda t: (t.get("data", ""), t.get("ora_inizio", "")),
            reverse=True,
        )
        # 1000 trips per annuale (~150KB), storico completo via servizio export_trips_csv
        return {"trips": trips[:1000], "total": len(trips)}


class ListaRicariche(MateSensor):
    """Ricariche filtrate dai select tipo/periodo, con totali."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_lista_ricariche"
        self._attr_name = f"{name} Lista Ricariche"
        self._attr_native_unit_of_measurement = "ricariche"
        self._attr_icon = "mdi:format-list-checks"

    @property
    def native_value(self):
        return self.coordinator.data["charges_filtered"]["n"]

    @property
    def extra_state_attributes(self):
        cf = self.coordinator.data["charges_filtered"]
        return {
            "items": cf["items"][:30],
            "total": cf["n"],
            "tipo": cf["tipo"],
            "periodo": cf["periodo"],
            "totale_kwh": cf["kwh"],
            "totale_costo": cf["costo"],
        }


class ReportGenerale(MateSensor):
    """Tabelle General/Settimanale/Mensile come attributi (per le dashboard)."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_report_generale"
        self._attr_name = f"{name} Report Generale"
        self._attr_icon = "mdi:table-large"

    @property
    def native_value(self):
        return len(self.coordinator.data["report"]["mensile"])

    @property
    def extra_state_attributes(self):
        return dict(self.coordinator.data["report"])


# -------------------------------------------------------------- salute batteria
class EfficienzaRicarica(MateSensor):
    """Efficienza dell'ultima ricarica a casa (mai sopra il 100%)."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_eff_ricarica"
        self._attr_name = f"{name} Efficienza Ricarica"
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:battery-charging-medium"

    @property
    def native_value(self):
        return self.coordinator.data.get("health", {}).get("last_eff", 0.0)


class PerditeRicarica(MateSensor):
    """Energia dispersa nell'ultima ricarica (kWh AC - kWh teorici in batteria)."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_perdite_ricarica"
        self._attr_name = f"{name} Perdite Ultima Ricarica"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_icon = "mdi:lightning-bolt-circle"

    @property
    def native_value(self):
        health = self.coordinator.data.get("health", {})
        perdite = health.get("last_perdite_kwh", 0.0)
        eff = health.get("last_eff", 0.0)
        self._attr_extra_state_attributes = {"percentuale": round(100.0 - eff, 1) if eff else 0.0}
        return perdite


class SohStimato(MateSensor):
    """State of Health stimato dalle ricariche piene a casa."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_soh_stimato"
        self._attr_name = f"{name} SOH Stimato"
        self._attr_native_unit_of_measurement = "%"
        self._attr_icon = "mdi:heart-pulse"

    @property
    def native_value(self):
        return self.coordinator.data.get("health", {}).get("soh_stimato", 0.0)

    @property
    def extra_state_attributes(self):
        health = self.coordinator.data.get("health", {})
        return {
            "soh_ufficiale": self.coordinator._setting_num("soh_official", 100.0),
            "ultima_ricarica_delta_pct": health.get("last_delta_pct"),
            "sessions": health.get("sessions", [])[-30:],
        }


# -------------------------------------------------------------- salute extra
class EnergiaBatteriaUltimaRicarica(MateSensor):
    """Energia effettivamente entrata in batteria nell'ultima ricarica a casa."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_batteria_ultima"
        self._attr_name = f"{name} Energia Batteria Ultima Ricarica"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_icon = "mdi:battery-arrow-up"

    @property
    def native_value(self):
        return self.coordinator.data.get("health", {}).get("last_batteria_kwh", 0.0)

    @property
    def extra_state_attributes(self):
        health = self.coordinator.data.get("health", {})
        return {
            "dalla_rete_kwh": health.get("last_rete_kwh"),
            "dispersa_kwh": health.get("last_perdite_kwh"),
        }


class KwhPer1Pct(MateSensor):
    """kWh corrispondenti a 1% di batteria (capacita' x SOH ufficiale)."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_kwh_per_1pct"
        self._attr_name = f"{name} kWh per 1% Batteria"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_icon = "mdi:percent"

    @property
    def native_value(self):
        return self.coordinator.data.get("kwh_per_1pct", 0.0)


class Tagliandi(MateSensor):
    """Registro tagliandi: costo totale, prossimo scadenza km."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_tagliandi"
        self._attr_name = f"{name} Tagliandi"
        self._attr_native_unit_of_measurement = "€"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:wrench"

    @property
    def native_value(self):
        return self.coordinator.data.get("maintenance", {}).get("costo_totale", 0.0)

    @property
    def extra_state_attributes(self):
        m = self.coordinator.data.get("maintenance", {})
        return {
            "items": m.get("items", []),
            "n": m.get("n", 0),
            "ultimo_km": m.get("ultimo_km"),
            "prossimo_km": m.get("prossimo_km"),
            "intervallo_km": m.get("intervallo"),
        }


class RisparmioExtra(MateSensor):
    """Risparmio aggiuntivo: tagliandi evitati, bollo, totale netto."""

    LABELS = {
        "tagliandi": ("Risparmio Tagliandi vs", "mdi:wrench-clock"),
        "bollo": ("Risparmio Bollo vs", "mdi:file-certificate"),
        "netto": ("Risparmio Netto vs", "mdi:cash-check"),
    }

    def __init__(self, coordinator, name, key):
        super().__init__(coordinator, name)
        self._key = key
        label, icon = self.LABELS[key]
        self._attr_unique_id = f"{coordinator.entry.entry_id}_risparmio_{key}"
        self._attr_name = f"{label} {coordinator.fuel_label}"
        self._attr_native_unit_of_measurement = "€"
        self._attr_icon = icon

    @property
    def native_value(self):
        return self.coordinator.data.get("savings", {}).get(self._key, 0.0)

    @property
    def extra_state_attributes(self):
        s = self.coordinator.data.get("savings", {})
        if self._key == "tagliandi":
            return {
                "tagliandi_termici_equivalenti": s.get("tagliandi_n"),
                "spesa_termica_teoria": s.get("tagliandi_teoria"),
                "spesa_reale_elettrica": s.get("tagliandi_reale"),
                "formula": "n. tagliandi termici x costo termico - spesa reale EV",
            }
        return {}


# -------------------------------------------------------------- extra v1.2
class DrainFermo(MateSensor):
    """Vampire drain: SoC persa da fermo oggi (auto ferma, non in carica)."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_drain_oggi"
        self._attr_name = f"{name} Batteria Persa da Fermo Oggi"
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:battery-clock"

    @property
    def native_value(self):
        return self.coordinator.data.get("drain_oggi_pct", 0.0)

    @property
    def extra_state_attributes(self):
        d = self.coordinator.data
        return {"equivalente_kwh": d.get("drain_oggi_kwh")}


class ConsumoZona(MateSensor):
    """Efficienza aggregata per rotta (zona partenza -> zona arrivo)."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_consumo_zona"
        self._attr_name = f"{name} Consumo per Zona"
        self._attr_native_unit_of_measurement = "rotte"
        self._attr_icon = "mdi:routes"

    @property
    def native_value(self):
        return len(self.coordinator.data.get("zone_routes", []))

    @property
    def extra_state_attributes(self):
        d = self.coordinator.data
        return {
            "rotte": d.get("zone_routes", []),
            "migliore_rotta": d.get("zone_best"),
            "peggior_rotta": d.get("zone_worst"),
        }


class CO2Risparmiata(MateSensor):
    """CO2 evitata rispetto all'auto termica equivalente."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_co2"
        self._attr_name = f"{name} CO2 Risparmiata"
        self._attr_native_unit_of_measurement = "kg"
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:molecule-co2"

    @property
    def native_value(self):
        return self.coordinator.data.get("co2", {}).get("totale", 0.0)

    @property
    def extra_state_attributes(self):
        co2 = self.coordinator.data.get("co2", {})
        return {
            "quest_anno": co2.get("anno"),
            "emesso_termica": co2.get("termica"),
            "emesso_rete": co2.get("ev"),
        }


class Scadenze(MateSensor):
    """Giorni rimasti alla scadenza piu' vicina (bollo/revisione/assicurazione)."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_scadenze"
        self._attr_name = f"{name} Prossima Scadenza"
        self._attr_native_unit_of_measurement = "gg"
        self._attr_icon = "mdi:calendar-alert"

    @property
    def native_value(self):
        scad = self.coordinator.data.get("scadenze", [])
        return scad[0]["giorni"] if scad else 0

    @property
    def extra_state_attributes(self):
        return {"scadenze": self.coordinator.data.get("scadenze", [])}


class ViaggioEstremo(MateSensor):
    """Viaggio piu' efficiente e piu' vorace del mese."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_viaggio_estremo"
        self._attr_name = f"{name} Viaggio Top/Stop del Mese"
        self._attr_native_unit_of_measurement = "kWh/100km"
        self._attr_icon = "mdi:trophy"

    @property
    def native_value(self):
        best = self.coordinator.data.get("best_trip")
        return best.get("kwh_per_100km") if best else 0.0

    @property
    def extra_state_attributes(self):
        d = self.coordinator.data
        best = d.get("best_trip") or {}
        worst = d.get("worst_trip") or {}
        return {
            "migliore": best and {k: best.get(k) for k in ("data", "ora_inizio", "km", "kwh_per_100km")},
            "peggiore": worst and {k: worst.get(k) for k in ("data", "ora_inizio", "km", "kwh_per_100km")},
        }


class EnergiaCasaTotale(MateSensor):
    """Energia totale caricata a casa (per Energy Dashboard)."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_energia_casa_tot"
        self._attr_name = f"{name} Energia Caricata Casa (totale)"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:home-lightning-bolt"

    @property
    def native_value(self):
        return self.coordinator.data.get("energia_casa_totale", 0.0)


# --------------------------------------------------------- percorrenza / assicurazione
class Percorrenza(MateSensor):
    """Tabella Percorrenza: % usata, kWh usati/caricati e km per ogni periodo."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_percorrenza"
        self._attr_name = f"{name} Percorrenza"
        self._attr_native_unit_of_measurement = "righe"
        self._attr_icon = "mdi:car-clock"

    @property
    def native_value(self):
        return len(self.coordinator.data.get("percorrenza", []))

    @property
    def extra_state_attributes(self):
        return {"righe": self.coordinator.data.get("percorrenza", [])}


class Assicurazione(MateSensor):
    """Giorni alla scadenza assicurazione + costo annuo."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_assicurazione"
        self._attr_name = f"{name} Assicurazione"
        self._attr_native_unit_of_measurement = "gg"
        self._attr_icon = "mdi:shield-car"

    @property
    def native_value(self):
        from datetime import date as _date
        data = self.coordinator.data.get("assicurazione", {}).get("data", "")
        if not data:
            return 0
        try:
            d0 = _date.fromisoformat(str(data))
        except ValueError:
            return 0
        oggi = _date.today()
        prossima = _date(oggi.year, d0.month, d0.day)
        if prossima < oggi:
            try:
                prossima = _date(oggi.year + 1, d0.month, d0.day)
            except ValueError:
                return 0
        return (prossima - oggi).days

    @property
    def extra_state_attributes(self):
        return dict(self.coordinator.data.get("assicurazione", {}))


class FvMese(MateSensor):
    """kWh caricati dal fotovoltaico questo mese."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_fv_mese"
        self._attr_name = f"{name} Ricaricato Fotovoltaico Mese"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:solar-power"

    @property
    def native_value(self):
        return self.coordinator.data.get("fv_mese", 0.0)


class FvTotale(MateSensor):
    """Energia totale caricata dal fotovoltaico (per Energy Dashboard: fonte solare)."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, name)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_fv_totale"
        self._attr_name = f"{name} Energia Caricata Fotovoltaico (totale)"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:solar-power-variant"

    @property
    def native_value(self):
        return self.coordinator.data.get("energia_fv_totale", 0.0)
