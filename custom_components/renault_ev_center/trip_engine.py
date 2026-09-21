"""Motore viaggi: rileva i viaggi dall'andamento dell'odometro."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any


def aggregate(trips: list[dict]) -> dict[str, float]:
    """Aggrega una lista di viaggi in statistiche di sintesi."""
    if not trips:
        return {
            "n_trip": 0,
            "km_totali": 0.0,
            "kwh_totali": 0.0,
            "kwh_per_100km": 0.0,
            "durata_totale_min": 0,
            "batteria_delta_totale": 0.0,
        }
    km_tot = round(sum(float(t.get("km", 0)) for t in trips), 1)
    kwh_tot = round(sum(float(t.get("kwh_consumati", 0)) for t in trips), 2)
    dur_tot = int(sum(int(t.get("durata_min", 0)) for t in trips))
    batt_tot = round(sum(float(t.get("batteria_delta", 0)) for t in trips), 1)
    eff = round(kwh_tot / km_tot * 100, 2) if km_tot > 0 else 0.0
    return {
        "n_trip": len(trips),
        "km_totali": km_tot,
        "kwh_totali": kwh_tot,
        "kwh_per_100km": eff,
        "durata_totale_min": dur_tot,
        "batteria_delta_totale": batt_tot,
    }


def group_by_day(trips: list[dict]) -> list[dict]:
    """Raggruppa i viaggi per giorno (dal più recente)."""
    per_giorno: dict[str, list[dict]] = {}
    for t in trips:
        d = t.get("data", "")
        if d:
            per_giorno.setdefault(d, []).append(t)

    risultato = []
    for giorno in sorted(per_giorno.keys(), reverse=True):
        agg = aggregate(per_giorno[giorno])
        risultato.append(
            {
                "data": giorno,
                "n_trip": agg["n_trip"],
                "km": agg["km_totali"],
                "kwh": agg["kwh_totali"],
                "kwh_per_100km": agg["kwh_per_100km"],
                "batt_delta": agg["batteria_delta_totale"],
                "durata_min": agg["durata_totale_min"],
            }
        )
    return risultato


class TripEngine:
    """Stato del viaggio in corso + chiusura per timeout."""

    def __init__(self, timeout_minuti: int = 20, min_km: float = 0.5,
                 min_minutes: int = 2, capacity_kwh: float = 60.0, tz=None,
                 park_threshold_min: float = 90.0, avg_kmh: float = 30.0) -> None:
        self.timeout_minuti = timeout_minuti
        self.min_km = min_km
        self.min_minutes = min_minutes
        self.capacity_kwh = capacity_kwh
        self.tz = tz
        # se l'auto resta ferma più di N minuti, l'orario di partenza si stima
        # (km / velocità media): il cloud Renault aggiorna solo a motore spento.
        self.park_threshold_min = park_threshold_min
        self.avg_kmh = avg_kmh
        self.active = False
        self.mileage_start = 0.0
        self.battery_start = 0.0
        self.ts_start = 0.0
        self.ts_last_change = 0.0
        self.mono_start = 0.0
        self.mono_last_change = 0.0
        self.zone_start = "unknown"
        self.mileage_now = 0.0
        self.battery_now = 0.0
        self.lat_last: float | None = None
        self.lon_last: float | None = None
        self.lat_start: float | None = None
        self.lon_start: float | None = None
        self.stima_orario = False
        self.arrived = False
        self.seed_odometer: float | None = None
        self.seed_battery = 0.0
        self.seed_ts = 0.0
        self.seed_mono = 0.0
        self.seed_zone = "unknown"
        self.seed_lat: float | None = None
        self.seed_lon: float | None = None

    def restore(self, data: dict[str, Any]) -> None:
        self.active = bool(data.get("active", False))
        self.mileage_start = float(data.get("mileage_start", 0))
        self.battery_start = float(data.get("battery_start", 0))
        self.ts_start = float(data.get("ts_start", 0))
        self.ts_last_change = float(data.get("ts_last_change", 0))
        self.mono_start = float(data.get("mono_start", 0) or data.get("ts_start", 0))
        self.mono_last_change = float(data.get("mono_last_change", 0) or data.get("ts_last_change", 0))
        self.zone_start = data.get("zone_start", "unknown")
        self.mileage_now = float(data.get("mileage_now", 0))
        self.battery_now = float(data.get("battery_now", 0))
        self.lat_start = data.get("lat_start")
        self.lon_start = data.get("lon_start")
        self.stima_orario = bool(data.get("stima_orario", False))

    def dump(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "mileage_start": self.mileage_start,
            "battery_start": self.battery_start,
            "ts_start": self.ts_start,
            "ts_last_change": self.ts_last_change,
            "mono_start": self.mono_start,
            "mono_last_change": self.mono_last_change,
            "zone_start": self.zone_start,
            "mileage_now": self.mileage_now,
            "battery_now": self.battery_now,
            "lat_start": self.lat_start,
            "lon_start": self.lon_start,
            "stima_orario": self.stima_orario,
        }

    def tick(self, odometer: float, battery_pct: float, zone: str,
             eff_live_kwh_100km: float, now_wall: float | None = None,
             now_mono: float | None = None,
             lat: float | None = None, lon: float | None = None) -> tuple[bool, dict | None]:
        """Elabora un campione. Ritorna (viaggio_aperto, viaggio_chiuso|None)."""
        opened = False
        closed = None
        now_wall = now_wall if now_wall is not None else time.time()
        now_mono = now_mono if now_mono is not None else time.monotonic()

        if odometer <= 0:
            return False, None

        # movimento GPS dal campione precedente (copre "fuori -> fuori")
        moved_gps = (
            lat is not None and lon is not None
            and self.lat_last is not None and self.lon_last is not None
            and (abs(lat - self.lat_last) > 0.0005 or abs(lon - self.lon_last) > 0.0005)
        )

        if not self.active:
            # AUTO FERMA: aggiorno solo il "seed" (ultimo stato da fermo).
            # Apro il viaggio SOLO se c'è movimento reale dal seed → niente "in movimento" a auto spenta.
            if self.seed_odometer is not None and (
                abs(odometer - self.seed_odometer) > 0.05
                or (self.seed_battery - battery_pct) >= 1.0
                or moved_gps
            ):
                self.active = True
                opened = True
                self.mileage_start = self.seed_odometer
                self.battery_start = self.seed_battery
                # Se l'auto è rimasta ferma a lungo (cloud Renault che aggiorna solo a
                # motore spento) l'ultimo campione "da ferma" è l'ORARIO DI SOSTA, non la
                # partenza: in quel caso stimo la partenza da km e velocità media.
                km_gap = abs(odometer - self.seed_odometer)
                gap_min = (now_wall - self.seed_ts) / 60.0
                self.stima_orario = False
                if gap_min > self.park_threshold_min and km_gap > 0.5:
                    self.ts_start = now_wall - min(gap_min, km_gap / max(self.avg_kmh, 10.0) * 60.0) * 60.0
                    self.stima_orario = True
                else:
                    self.ts_start = self.seed_ts
                self.ts_last_change = now_wall
                self.mono_start = now_mono
                self.mono_last_change = now_mono
                self.zone_start = self.seed_zone or zone or "unknown"
                self.mileage_now = odometer
                self.battery_now = battery_pct
                self.lat_start = self.seed_lat
                self.lon_start = self.seed_lon
                self.lat_last = lat
                self.lon_last = lon
                # se nello stesso campione c'è già lo scarto chilometrico, l'auto è
                # arrivata (cloud Renault che riporta odometro+GPS a motore spento)
                self.arrived = bool(moved_gps and km_gap > 0.5)
                return opened, closed
            self.seed_odometer = odometer
            self.seed_battery = battery_pct
            self.seed_ts = now_wall
            self.seed_mono = now_mono
            self.seed_zone = zone
            self.seed_lat = lat
            self.seed_lon = lon
            self.lat_last = lat
            self.lon_last = lon
            return False, None

        # --- viaggio attivo ---
        prev_mileage = self.mileage_now
        prev_battery = self.battery_now
        self.mileage_now = odometer
        self.battery_now = battery_pct
        if abs(odometer - prev_mileage) > 0.05 or (prev_battery - battery_pct) >= 1.0 or moved_gps:
            self.ts_last_change = now_wall
            self.mono_last_change = now_mono
        # arrivo: Renault aggiorna odometro+posizione a spegnimento →
        # se nello stesso campione cambia la posizione E salta l'odometro, l'auto è spenta all'arrivo.
        self.arrived = bool(moved_gps and abs(odometer - prev_mileage) > 0.5)
        if lat is not None:
            self.lat_last = lat
        if lon is not None:
            self.lon_last = lon
        return opened, closed

    def should_close(self, now_mono: float | None = None) -> bool:
        if not self.active:
            return False
        mono = now_mono if now_mono is not None else time.monotonic()
        elapsed_min = (mono - self.mono_last_change) / 60.0
        return elapsed_min >= self.timeout_minuti

    def close(self, zone_arrivo: str, eff_live_kwh_100km: float,
              now_wall: float | None = None) -> dict | None:
        """Finalizza il viaggio e ritorna il record (None se scartato)."""
        if not self.active:
            return None
        now = now_wall if now_wall is not None else time.time()
        km = round(self.mileage_now - self.mileage_start, 1)
        batt_delta = round(self.battery_start - self.battery_now, 1)
        durata_min = int((now - self.ts_start) / 60)

        self.active = False
        self.seed_odometer = None
        if km < self.min_km or durata_min < self.min_minutes:
            return None

        # PRIORITÀ al SoC REALE della batteria: il consumo effettivo è il delta % (× capacità).
        # L'efficienza "live" (kWh dei viaggi) sbaglia sui tragitti corti (media non significativa).
        if batt_delta > 0:
            kwh_consumati = round(batt_delta / 100 * self.capacity_kwh, 2)
            kwh_per_100 = round(kwh_consumati / km * 100, 2) if km > 0 else 0.0
        elif eff_live_kwh_100km and eff_live_kwh_100km > 0:
            kwh_consumati = round(km * eff_live_kwh_100km / 100, 2)
            kwh_per_100 = round(eff_live_kwh_100km, 2)
        else:
            kwh_consumati = 0.0
            kwh_per_100 = 0.0

        ts_inizio = datetime.fromtimestamp(self.ts_start, self.tz) if self.tz else datetime.fromtimestamp(self.ts_start)
        ts_fine = datetime.fromtimestamp(now, self.tz) if self.tz else datetime.fromtimestamp(now)
        return {
            "id": int(self.ts_start),
            "data": ts_inizio.strftime("%Y-%m-%d"),
            "ora_inizio": ts_inizio.strftime("%H:%M"),
            "ora_fine": ts_fine.strftime("%H:%M"),
            "durata_min": durata_min,
            "km": km,
            "mileage_inizio": round(self.mileage_start, 1),
            "mileage_fine": round(self.mileage_now, 1),
            "batteria_inizio": round(self.battery_start, 1),
            "batteria_fine": round(self.battery_now, 1),
            "batteria_delta": batt_delta,
            "kwh_consumati": kwh_consumati,
            "kwh_per_100km": kwh_per_100,
            "zona_partenza": self.zone_start,
            "zona_arrivo": zone_arrivo or "unknown",
            "stima_orario": self.stima_orario,
            "gps_partenza": ({"lat": round(self.lat_start, 5), "lon": round(self.lon_start, 5)}
                             if self.lat_start is not None and self.lon_start is not None else {}),
        }
