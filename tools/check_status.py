"""check_status.py — Verifica lo stato del progetto Renault EV Center e indica cosa riprendere.

Uso:  py tools\\check_status.py
Esce con codice 0 se tutto ok, 1 se ci sono problemi.
"""
import glob
import os
import py_compile
import re
import sys
import json

try:
    import yaml
except ImportError:
    yaml = None

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CC = os.path.join(BASE, "custom_components", "renault_ev_center")

problemi = []
done = []


def ok(msg):
    done.append(msg)
    print(f"  OK   {msg}")


def bad(msg):
    problemi.append(msg)
    print(f"  ERR  {msg}")


print("=" * 62)
print("STATO PROGETTO RENAULT EV CENTER")
print("=" * 62)

# ---------------------------------------------------------------- file chiave
print("\n[1] File principali")
attesi = [
    "custom_components/renault_ev_center/__init__.py",
    "custom_components/renault_ev_center/config_flow.py",
    "custom_components/renault_ev_center/coordinator.py",
    "custom_components/renault_ev_center/sensor.py",
    "custom_components/renault_ev_center/binary_sensor.py",
    "custom_components/renault_ev_center/button.py",
    "custom_components/renault_ev_center/number.py",
    "custom_components/renault_ev_center/select.py",
    "custom_components/renault_ev_center/store.py",
    "custom_components/renault_ev_center/meters.py",
    "custom_components/renault_ev_center/trip_engine.py",
    "custom_components/renault_ev_center/const.py",
    "custom_components/renault_ev_center/manifest.json",
    "custom_components/renault_ev_center/services.yaml",
    "custom_components/renault_ev_center/strings.json",
    "custom_components/renault_ev_center/translations/it.json",
    "custom_components/renault_ev_center/translations/en.json",
    "hacs.json", "README.md", "LICENSE", "CHANGELOG.md", "agent.md",
    "VERSION",
    "dashboards/01_panoramica.yaml",
    "dashboards/02_viaggi.yaml",
    "dashboards/03_statistiche.yaml",
    "dashboards/04_ricariche.yaml",
    "dashboards/05_salute_batteria.yaml",
    "dashboards/06_impostazioni.yaml",
    "dashboards/07_extra.yaml",
    "dashboards/08_manutenzione.yaml",
    "themes/renault-giallo.yaml",
    "themes/renault-blu.yaml",
    "themes/renault-luce.yaml",
    "themes/renault-verde.yaml",
    "themes/renault-aviation.yaml",
    "custom_components/renault_ev_center/dashboard.py",
    "custom_components/renault_ev_center/www/renault-ev-center-card.js",
    "www/renault-ev-center-card.js",
    "preview/card_demo.html",
    "custom_components/renault_ev_center/switch.py",
    "custom_components/renault_ev_center/time.py",
    "dashboards/10_automazioni.yaml",
    "dashboards/11_mobile.yaml",
    "dashboards/12_gestione.yaml",
    "examples/automazioni_esempio.yaml",
    "docs/INSTALLAZIONE.md", "docs/INSTALLATION.md",
]
for rel in attesi:
    if os.path.isfile(os.path.join(BASE, rel)):
        ok(rel)
    else:
        bad(f"manca il file {rel}")

# ---------------------------------------------------------------- python
print("\n[2] Sintassi Python")
for path in sorted(glob.glob(os.path.join(CC, "*.py"))):
    try:
        py_compile.compile(path, doraise=True)
        ok(os.path.basename(path))
    except py_compile.PyCompileError as e:
        bad(f"{os.path.basename(path)}: {e}")

# ---------------------------------------------------------------- yaml/json
print("\n[3] YAML / JSON")
for path in (
    sorted(glob.glob(os.path.join(BASE, "dashboards", "*.yaml")))
    + sorted(glob.glob(os.path.join(BASE, "examples", "*.yaml")))
    + [os.path.join(CC, "services.yaml"), os.path.join(CC, "manifest.json"),
       os.path.join(CC, "strings.json"), os.path.join(CC, "translations", "it.json"),
       os.path.join(CC, "translations", "en.json"), os.path.join(BASE, "hacs.json")]
):
    nome = os.path.basename(path)
    try:
        with open(path, encoding="utf-8") as fh:
            if path.endswith(".json"):
                json.load(fh)
            elif yaml is not None:
                yaml.safe_load(fh)
        ok(nome)
    except Exception as e:
        bad(f"{nome}: {e}")

# ---------------------------------------------------------------- coerenza entità
print("\n[4] Coerenza entità dashboard <-> integrazione")


def slugify(text):
    s = re.sub(r"[^\w\s]", "", text.lower())
    return re.sub(r"\s+", "_", s.strip())


NAME = "Renault"
friendly = [
    f"{NAME} Km per kWh", f"{NAME} kWh per 100km",
    f"{NAME} Batteria kWh Disponibili",
    f"{NAME} kWh Totali Consumati", f"{NAME} Batteria % per 100km",
    f"{NAME} Costo per km", f"{NAME} Costo per 100 km",
    *[f"{NAME} Km {l}" for l in ("Giornalieri", "Settimanali", "Mensili", "Annuali")],
    *[f"{NAME} Energia Caricata {l}" for l in ("Giornaliera", "Settimanale", "Mensile", "Annuale", "Totale")],
    *[f"{NAME} Costo Ricarica {l}" for l in ("Giornaliero", "Settimanale", "Mensile", "Annuale", "Totale")],
    f"{NAME} Batteria % Caricata Oggi", f"{NAME} Batteria % Scaricata Oggi",
    *[f"{NAME} Energia Batteria {l}" for l in ("Giornaliera", "Settimanale", "Mensile", "Annuale")],
    f"{NAME} Tempo Ricarica Stimato", f"{NAME} Ora Completamento Ricarica",
    f"{NAME} Costo Ricarica Corrente Stimato", f"{NAME} Tipo Ricarica Attuale",
    f"{NAME} Trip Attivo", f"{NAME} Km Trip Corrente", f"{NAME} Durata Trip Corrente",
    f"{NAME} Ultimo Trip", f"{NAME} Trip Completati Oggi", f"{NAME} Km Oggi (Trip)",
    f"{NAME} Statistiche Viaggi", f"{NAME} Viaggi Recenti", f"{NAME} Storico Giornaliero",
    f"{NAME} Archivio Viaggi", f"{NAME} Lista Ricariche", f"{NAME} Report Generale",
    f"{NAME} Ultima Ricarica", f"{NAME} Ricariche Oggi", f"{NAME} Ricariche Mese",
    *[f"{NAME} Risparmio {l} vs Diesel" for l in ("Totale", "Mese", "Anno")],
    f"{NAME} Wallbox Potenza",
    f"{NAME} Efficienza Ricarica", f"{NAME} Perdite Ultima Ricarica", f"{NAME} SOH Stimato",
    f"{NAME} Energia Batteria Ultima Ricarica", f"{NAME} kWh per 1% Batteria",
    f"{NAME} Tagliandi",
    *[f"{NAME} Risparmio {l} vs Diesel" for l in ("Tagliandi", "Bollo", "Netto")],
    f"{NAME} Batteria Persa da Fermo Oggi", f"{NAME} Consumo per Zona",
    f"{NAME} CO2 Risparmiata", f"{NAME} Prossima Scadenza",
    f"{NAME} Viaggio Top/Stop del Mese", f"{NAME} Energia Caricata Casa (totale)",
    f"{NAME} Percorrenza", f"{NAME} Assicurazione", f"{NAME} Ricaricato Fotovoltaico Mese",
    f"{NAME} Energia Caricata Fotovoltaico (totale)",
]
generated = {"sensor." + slugify(f) for f in friendly}
generated |= {
    "binary_sensor." + slugify(f"{NAME} In Carica"),
    "binary_sensor." + slugify(f"{NAME} Wallbox in Carica"),
    "number." + slugify(f"{NAME} Costo Energia Casa"),
    "number." + slugify(f"{NAME} Costo Colonnina"),
    "number." + slugify(f"{NAME} Costo Fotovoltaico"),
    "number." + slugify(f"{NAME} Capacita Batteria"),
    "number." + slugify(f"{NAME} Obiettivo Ricarica"),
    "number." + slugify(f"{NAME} SOH Ufficiale"),
    "number." + slugify(f"{NAME} Costo Assicurazione"),
    "time." + slugify(f"{NAME} Promemoria Inizio"),
    "time." + slugify(f"{NAME} Promemoria Fine"),
    "time." + slugify(f"{NAME} Carica Orario Avvio"),
    "time." + slugify(f"{NAME} Carica Orario Stop"),
    "number." + slugify(f"{NAME} Batteria Minima Promemoria"),
    "number." + slugify(f"{NAME} Carica Avvio Sotto"),
    "number." + slugify(f"{NAME} Carica Ferma Sopra"),
    "select." + slugify(f"{NAME} Filtro Tipo Ricarica"),
    "select." + slugify(f"{NAME} Filtro Periodo Ricariche"),
    "select." + slugify(f"{NAME} Filtro Anno Ricariche"),
    "button." + slugify(f"{NAME} Chiudi Viaggio Ora"),
    "button." + slugify(f"{NAME} Esporta Viaggi CSV"),
    "button." + slugify(f"{NAME} Reset Contatori Km"),
    "button." + slugify(f"{NAME} Reset Contatori Energia"),
    "button." + slugify(f"{NAME} Reset Contatori Costi"),
    "switch." + slugify(f"{NAME} Bilanciamento Solare"),
    "number." + slugify(f"{NAME} Bilanciamento Ampere Minimi"),
    "number." + slugify(f"{NAME} Bilanciamento Ampere Massimi"),
    "number." + slugify(f"{NAME} Priorita Batteria Casa"),
}
ALLOWED = {
    "sensor.battery_level", "sensor.battery_autonomy", "sensor.mileage",
    "device_tracker.location", "binary_sensor.charging", "sensor.charge_state",
    "sensor.plug_state", "binary_sensor.plugged_in", "sensor.charging_remaining_time",
    "button.start_air_conditioner", "button.start_charge", "number.charge_target",
}
for path in sorted(glob.glob(os.path.join(BASE, "dashboards", "*.yaml"))):
    txt = open(path, encoding="utf-8").read()
    txt = "\n".join(l.split("#")[0] if not l.lstrip().startswith("#") else "" for l in txt.splitlines())
    for e in sorted(set(re.findall(r"\b((?:sensor|binary_sensor|device_tracker|button|number|select)\.[a-z0-9_]+)", txt))):
        if e not in generated and e not in ALLOWED:
            bad(f"{os.path.basename(path)}: entità '{e}' non generata dall'integrazione")
if not problemi or all("entità" not in p for p in problemi):
    ok(f"{len(generated)} entità generate, dashboard coerenti")

# ---------------------------------------------------------------- versione
print("\n[5b] Versione")
try:
    version = open(os.path.join(BASE, "VERSION"), encoding="utf-8").read().strip()
    if version:
        ok(f"version {version}")
    else:
        bad("VERSION vuoto")
except Exception as e:
    version = None
    bad(f"VERSION illeggibile: {e}")
try:
    man = json.load(open(os.path.join(CC, "manifest.json"), encoding="utf-8"))
    if version and man.get("version") == version:
        ok("manifest version = VERSION")
    else:
        bad(f"manifest version = {man.get('version')} (attesa {version})")
except Exception as e:
    bad(f"manifest.json illeggibile: {e}")

# ---------------------------------------------------------------- preview
print("\n[5] Preview")
p_old = os.path.join(BASE, "preview", "index.html")
p_new = os.path.join(BASE, "preview", "index_new.html")
if os.path.isfile(p_new):
    bad("preview/index_new.html esiste ancora: cancellalo e tieni solo index.html")
elif os.path.isfile(p_old):
    txt = open(p_old, encoding="utf-8").read()
    if "Salute batteria" in txt and "Manutenzione" in txt and f"v{version}" in txt:
        ok(f"preview/index.html (8 tab, palette, v{version})")
    else:
        bad("preview/index.html non aggiornato alla versione corrente")
else:
    bad("preview/index.html mancante")

# ---------------------------------------------------------------- todo da agent.md
print("\n[6] Attività aperte (da agent.md sezione 3)")
agent = os.path.join(BASE, "agent.md")
if os.path.isfile(agent):
    aperte = [l.strip() for l in open(agent, encoding="utf-8")
              if l.strip().startswith("- [ ]")]
    if aperte:
        for a in aperte:
            print(f"  TODO {a[6:].strip()}")
    else:
        ok("nessuna attività aperta dichiarata in agent.md")

# ---------------------------------------------------------------- esito
print("\n" + "=" * 62)
if problemi:
    print(f"PROBLEMI: {len(problemi)}  → correggi quanto sopra e rilancia lo script")
    for p in problemi:
        print("  -", p)
    print("Riprendi il lavoro seguendo agent.md sezione 3 e 4.")
    sys.exit(1)
print(f"TUTTO OK ({len(done)} controlli superati). Progetto pronto per test/pubblicazione.")
