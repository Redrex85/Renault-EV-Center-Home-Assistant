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
                 min_minutes: int = 2, capacity_kwh: float = 60.0) -> None:
        self.timeout_minuti = timeout_minuti
        self.min_km = min_km
        self.min_minutes = min_minutes
        self.capacity_kwh = capacity_kwh
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
        }

    def tick(self, odometer: float, battery_pct: float, zone: str,
             eff_live_kwh_100km: float, now_wall: float | None = None,
             now_mono: float | None = None) -> tuple[bool, dict | None]:
        """Elabora un campione. Ritorna (viaggio_aperto, viaggio_chiuso|None)."""
        opened = False
        closed = None
        now_wall = now_wall if now_wall is not None else time.time()
        now_mono = now_mono if now_mono is not None else time.monotonic()

        if odometer <= 0:
            return False, None

        if not self.active:
            self.active = True
            opened = True
            self.mileage_start = odometer
            self.battery_start = battery_pct
            self.ts_start = now_wall
            self.ts_last_change = now_wall
            self.mono_start = now_mono
            self.mono_last_change = now_mono
            self.zone_start = zone or "unknown"
            self.mileage_now = odometer
            self.battery_now = battery_pct
            return opened, closed

        # aggiorna posizione attuale
        prev_mileage = self.mileage_now
        prev_battery = self.battery_now
        self.mileage_now = odometer
        self.battery_now = battery_pct
        # timeout solo su movimento reale (Renault: odometro solo a spegnimento,
        # batteria ogni 5-6'): mantiene il viaggio vivo anche mentre l'odometro è fermo
        if abs(odometer - prev_mileage) > 0.05 or abs(battery_pct - prev_battery) >= 0.3:
            self.ts_last_change = now_wall
            self.mono_last_change = now_mono
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
        if km < self.min_km or durata_min < self.min_minutes:
            return None

        if eff_live_kwh_100km and eff_live_kwh_100km > 0:
            kwh_consumati = round(km * eff_live_kwh_100km / 100, 2)
            kwh_per_100 = round(eff_live_kwh_100km, 2)
        elif batt_delta > 0:
            kwh_consumati = round(batt_delta / 100 * self.capacity_kwh, 2)
            kwh_per_100 = round(kwh_consumati / km * 100, 2) if km > 0 else 0.0
        else:
            kwh_consumati = 0.0
            kwh_per_100 = 0.0

        ts_inizio = datetime.fromtimestamp(self.ts_start)
        ts_fine = datetime.fromtimestamp(now)
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
        }
