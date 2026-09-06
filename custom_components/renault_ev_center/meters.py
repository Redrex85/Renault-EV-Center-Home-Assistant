"""Contatori per periodo (replica il comportamento di utility_meter)."""
from __future__ import annotations

from datetime import datetime


def period_keys(now: datetime) -> dict[str, str]:
    """Chiavi dei periodi correnti (giorno/settimana ISO/mese/anno)."""
    d = now.date()
    iso = d.isocalendar()
    return {
        "daily": d.strftime("%Y-%m-%d"),
        "weekly": "%s-W%02d" % (iso[0], iso[1]),
        "monthly": d.strftime("%Y-%m"),
        "yearly": str(d.year),
    }


class PeriodMeter:
    """Misura la differenza di una fonte cumulativa nel periodo (es. odometro → km)."""

    def __init__(self) -> None:
        self.key = ""
        self.baseline: float | None = None
        self.value = 0.0
        self.last = 0.0

    def to_dict(self) -> dict:
        return {"key": self.key, "baseline": self.baseline,
                "value": self.value, "last": self.last}

    @classmethod
    def from_dict(cls, data: dict | None) -> "PeriodMeter":
        obj = cls()
        if data:
            obj.key = data.get("key", "")
            baseline = data.get("baseline")
            obj.baseline = float(baseline) if baseline is not None else None
            obj.value = float(data.get("value", 0))
            obj.last = float(data.get("last", 0))
        return obj

    def tick(self, key_now: str, total_now: float | None) -> None:
        """total_now è il valore cumulativo della fonte (None se non disponibile)."""
        if self.key != key_now:
            # nuovo periodo: chiudi il precedente e riparti dal valore attuale
            self.last = round(self.value, 2)
            self.key = key_now
            self.baseline = total_now
            self.value = 0.0
        elif self.baseline is None and total_now is not None:
            # prima lettura utile del periodo
            self.baseline = total_now
        if total_now is not None and self.baseline is not None:
            v = total_now - self.baseline
            if v >= -0.5:  # tollera micro-inversioni di arrotondamento
                self.value = max(v, 0.0)


class DeltaMeter:
    """Somma gli incrementi positivi (o negativi) di un valore nel periodo."""

    def __init__(self, direction: str = "up") -> None:
        self.direction = direction  # "up" somma aumenti, "down" somma diminuzioni
        self.key = ""
        self.ref_last: float | None = None
        self.value = 0.0
        self.last = 0.0

    def to_dict(self) -> dict:
        return {"key": self.key, "ref_last": self.ref_last,
                "value": self.value, "last": self.last, "dir": self.direction}

    @classmethod
    def from_dict(cls, data: dict | None) -> "DeltaMeter":
        obj = cls(data.get("dir", "up") if data else "up")
        if data:
            obj.key = data.get("key", "")
            ref = data.get("ref_last")
            obj.ref_last = float(ref) if ref is not None else None
            obj.value = float(data.get("value", 0))
            obj.last = float(data.get("last", 0))
        return obj

    def tick(self, key_now: str, value_now: float | None,
             allow: bool = True, max_delta: float = 50.0) -> None:
        if self.key != key_now:
            self.last = round(self.value, 2)
            self.key = key_now
            self.value = 0.0
            self.ref_last = value_now
            return
        if value_now is None:
            return
        if self.ref_last is None:
            self.ref_last = value_now
            return
        delta = value_now - self.ref_last
        self.ref_last = value_now
        if not allow or delta == 0 or abs(delta) > max_delta:
            return
        if self.direction == "up" and delta > 0:
            self.value += delta
        elif self.direction == "down" and delta < 0:
            self.value += abs(delta)
