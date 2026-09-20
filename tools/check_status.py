"""check_status.py — Verifica lo stato del progetto Renault EV Center e indica cosa riprendere.

Uso:  py tools\\check_status.py
Esce con codice 0 se tutto ok, 1 se ci sono problemi.
"""
import glob
import os
import ast
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
       os.path.join(CC, "translations", "en.json"), os.path.join(CC, "translations", "fr.json"),
       os.path.join(BASE, "hacs.json")]
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
    f"{NAME} Ultima Ricarica", f"{NAME} Delta % Ultima Carica",
    f"{NAME} Ricariche Oggi", f"{NAME} Ricariche Mese",
    *[f"{NAME} Risparmio {l} vs Diesel" for l in ("Totale", "Mese", "Anno")],
    f"{NAME} Wallbox Potenza",
    f"{NAME} Efficienza Ricarica", f"{NAME} Perdite Ultima Ricarica", f"{NAME} SOH Stimato",
    f"{NAME} Energia Batteria Ultima Ricarica", f"{NAME} kWh per 1% Batteria",
    f"{NAME} Tagliandi",
    *[f"{NAME} Risparmio {l} vs Diesel" for l in ("Tagliandi", "Bollo", "Netto")],
    f"{NAME} Batteria Persa da Fermo Oggi", f"{NAME} Consumo per Zona",
    f"{NAME} CO2 Risparmiata", f"{NAME} Prossima Scadenza", f"{NAME} Programmazione",
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
    "number." + slugify(f"{NAME} Prezzo Carburante"),
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

print("\n[7] Riepilogo giornaliero")
try:
    import ast
    from jinja2 import Environment

    with open(os.path.join(CC, "coordinator.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    message = next(node.args[2] for node in ast.walk(tree)
                   if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                   and node.func.id == "_pn" and isinstance(node.args[0], ast.JoinedStr)
                   and node.args[0].values[0].value == "rec_sum_")
    template = Environment().from_string(eval(
        compile(ast.Expression(message), "<daily-summary>", "eval"),
        {"__builtins__": {}, "n": "renault"}))
    for energy, price, expected in (
        ("12", "0.25", "3.0 €"), ("0", "0.25", "0.0 €"),
        ("12", "0", "0.0 €"), ("unknown", "0.25", "non disponibile"),
        ("12", "unavailable", "non disponibile"),
    ):
        states = {"sensor.renault_energia_batteria_giornaliero": energy,
                  "number.renault_costo_energia_casa": price}
        rendered = template.render(states=lambda entity: states.get(entity, "unknown"))
        assert expected in rendered, rendered
        if energy == "12":
            assert "12.0 kWh" in rendered, rendered
    ok("riepilogo: consumo, costo, valori zero e dati mancanti")
except Exception as e:
    bad(f"riepilogo giornaliero: {e}")

print("\n[8] Contatori persistenti")
try:
    with open(os.path.join(CC, "coordinator.py"), encoding="utf-8") as fh:
        linee = fh.readlines()
    colpevoli = [i + 1 for i, l in enumerate(linee)
                 if re.search(r'self\.store\.data\["counters"\]\s*=', l)]
    assert not colpevoli, (
        "assegnazione che azzera i contatori (perde last_notify/balance_last): "
        f"coordinator.py:{colpevoli}")
    assert any('counters", {}).update(c)' in l for l in linee)
    ok("nessuna sovrascrittura di counters (last_notify/balance_last sopravvivono)")
except Exception as e:
    bad(f"contatori: {e}")

print("\n[9] Campi Configura tradotti")
try:
    const_src = open(os.path.join(CC, "const.py"), encoding="utf-8").read()
    valori = dict(re.findall(r'^(CONF_[A-Z0-9_]+)\s*=\s*"([^"]+)"', const_src, re.M))
    flow_src = open(os.path.join(CC, "config_flow.py"), encoding="utf-8").read()
    usati = {valori[c] for c in re.findall(r'vol\.(?:Optional|Required)\(\s*(CONF_[A-Z0-9_]+)', flow_src)
             if c in valori}
    for nome in ("strings.json",) + tuple(f"translations/{l}.json" for l in ("it", "en", "fr")):
        testo = open(os.path.join(CC, nome), encoding="utf-8").read()
        mancanti = sorted(k for k in usati if f'"{k}"' not in testo)
        assert not mancanti, f"{nome}: non tradotti {mancanti}"
    ok(f"{len(usati)} campi Configura presenti nelle 4 traduzioni")
except Exception as e:
    bad(f"traduzioni config: {e}")

print("\n[10] Energia ricarica misurata")
try:
    with open(os.path.join(CC, "coordinator.py"), encoding="utf-8") as fh:
        tree10 = ast.parse(fh.read())
    ns10: dict = {"_f": lambda v, d=0.0: float(v) if v not in (None, "") else d}
    for nome in ("_best_measured_delta", "_charge_energy"):
        fnn = next(n for n in tree10.body if isinstance(n, ast.FunctionDef) and n.name == nome)
        exec(compile(ast.Module(body=[fnn], type_ignores=[]), f"<{nome}>", "exec"), ns10)
    delta = ns10["_best_measured_delta"]
    assert delta([(10.0, 20.0), (5.0, 8.0)]) == 10.0
    assert round(delta([(100.0, 2.0), (50.0, 88.24)]), 2) == 38.24  # contatore sessione azzerato
    assert delta([(None, 5.0), (None, None)]) == 0.0
    assert delta([]) == 0.0
    en = ns10["_charge_energy"]
    assert en(38.24, 0, "Casa", 20, 80, 60) == (38.24, None)  # misura: vince sempre
    assert en(0, 12.5, "Casa", 20, 80, 60) == (12.5, "potenza_istantanea")  # integrale potenza
    assert (round(en(0, 0, "Pubblica", 20, 50, 60)[0], 2), en(0, 0, "Pubblica", 20, 50, 60)[1]) \
        == (18.0, "fuori_casa")  # stima dal SoC: caso normale fuori casa
    assert en(0, 0, "Casa", 20, 50, 60)[1] == "casa_senza_misura"  # a casa: ripiego da segnalare
    ok("energia ricarica: misura, integrale potenza, stima fuori casa / ripiego a casa")
except Exception as e:
    bad(f"energia ricarica: {e}")

print("\n[11] Auto-refresh pannello/card")
try:
    version = open(os.path.join(BASE, "VERSION"), encoding="utf-8").read().strip()
    for fname, const in (("renault-ev-center-panel.js", "REC_VER"),
                         ("renault-ev-center-card.js", "CARD_VER")):
        js = open(os.path.join(CC, "www", fname), encoding="utf-8").read()
        m = re.search(rf'const {const} = "([^"]+)"', js)
        assert m, f"{const} non trovato in {fname}"
        assert m.group(1) == version, f"{fname}: {const} {m.group(1)} != VERSION {version}"
    dash = open(os.path.join(CC, "dashboard.py"), encoding="utf-8").read()
    assert '"version": version' in dash, \
        "dashboard.py non passa la versione alla card: l'auto-refresh non scatta"
    assert 'version: str = ""' in dash, "async_setup_dashboard non accetta la versione"
    # la versione NON deve essere letta con I/O dentro l'event loop (era un blocking call)
    flow = open(os.path.join(CC, "__init__.py"), encoding="utf-8").read()
    assert "async_add_executor_job(_read_manifest_version)" in flow, \
        "la versione va letta in executor, non nell'event loop"
    assert "open(" not in open(os.path.join(CC, "const.py"), encoding="utf-8").read(), \
        "const.py non deve fare I/O (blocking call nell'event loop)"
    ok(f"REC_VER/CARD_VER = VERSION ({version}) · card dichiara la versione · letta in executor")
except Exception as e:
    bad(f"auto-refresh: {e}")

print("\n[12] Bilanciamento tag <div> nel pannello")
try:
    js = open(os.path.join(CC, "www", "renault-ev-center-panel.js"), encoding="utf-8").read()
    aperti = len(re.findall(r"<div\b", js))
    chiusi = len(re.findall(r"</div>", js))
    assert aperti == chiusi, (
        f"<div> sbilanciati: {aperti} aperti vs {chiusi} chiusi "
        "(un </div> orfano sposta tutte le pagine)/")
    ok(f"markup pannello bilanciato ({aperti} div)")
except Exception as e:
    bad(f"markup pannello: {e}")

print("\n[13] Versione compatibile HACS")
try:
    version = open(os.path.join(BASE, "VERSION"), encoding="utf-8").read().strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.\-]+)?", version), (
        f"VERSION '{version}' non valida: serve x.y.z oppure x.y.z-suffix "
        "(es. 1.0.10-beta). HACS prende la PRIMA release dell'elenco GitHub: "
        "con 4 numeri l'ordine si rompe (1.0.6.8 prima di 1.0.6.12) -> nessun aggiornamento"
    )
    kind = "beta/pre-release" if "-" in version else "stabile (semver x.y.z)"
    ok(f"VERSION {version} valida — {kind}")
except Exception as e:
    bad(f"versione HACS: {e}")

print("\n[14] Pannello: setConfig assegna _cfg prima di usarlo")
try:
    js = open(os.path.join(CC, "www", "renault-ev-center-panel.js"), encoding="utf-8").read()
    start = js.index("setConfig(config)")
    body = js[start:start + 900]           # corpo di setConfig: ampiamente sufficiente
    i_cfg = body.index("this._cfg = {")
    for call in ("this._checkVersion(", "this._startVersionWatch("):
        if call in body:
            assert body.index(call) > i_cfg, (
                f"{call} chiamata PRIMA di this._cfg = {{...}}: "
                "this._sid() legge _cfg.name -> TypeError, la card non si configura"
            )
    ok("_cfg assegnato prima di _checkVersion/_startVersionWatch")
except Exception as e:
    bad(f"setConfig: {e}")

print("\n[15] Costi/energia ricariche derivati dai record")
try:
    src = open(os.path.join(CC, "coordinator.py"), encoding="utf-8").read()
    # il bug: percorrenza/cost/wb_energy letti dai meter live (che restano 0 se lo stato
    # wallbox non è "charging" nel polling). Devono venire dai record salvati.
    assert "def _chg_sum(" in src, "manca _chg_sum: costi/energia non derivano dalle ricariche"
    assert '"wb_energy": {p: {"value": chg[p][0]' in src, "wb_energy non usa i record"
    assert '"cost": {p: {"value": chg[p][1]' in src, "cost non usa i record"
    assert 'chg["daily"][0]' in src and 'chg["monthly"][0]' in src, \
        "percorrenza.caricati non usa i record"
    # la vecchia fonte (meter live) non deve più comparire in percorrenza
    assert 'self.wb_meters["daily"].value' not in src, \
        "percorrenza.caricati usa ancora il meter live (resta 0)"
    ok("costi/energia ricariche sommati dai record (percorrenza, cost, wb_energy)")
except Exception as e:
    bad(f"costi ricariche: {e}")

print("\n[16] AC/DC e statistiche ricariche")
try:
    with open(os.path.join(CC, "coordinator.py"), encoding="utf-8") as fh:
        tree16 = ast.parse(fh.read())
    ns16: dict = {"_f": lambda v, d=0.0: float(v) if v not in (None, "") else d}
    fn16 = next(n for n in tree16.body
                if isinstance(n, ast.FunctionDef) and n.name == "_ac_dc_from_power")
    exec(compile(ast.Module(body=[fn16], type_ignores=[]), "<acdc>", "exec"), ns16)
    acdc = ns16["_ac_dc_from_power"]
    assert acdc(11.0) == "AC", "11 kW deve essere AC"
    assert acdc(22.0) == "AC", "22 kW (3 fase 32 A) resta AC"
    assert acdc(110.0) == "DC", "110 kW deve essere DC"
    assert acdc(0, 50.0) == "DC", "senza picco usa la media"
    assert acdc(0, 0) is None, "potenza ignota -> None"
    src16 = open(os.path.join(CC, "coordinator.py"), encoding="utf-8").read()
    assert '"charges_stats": cstats' in src16, "charges_stats non esposto nei dati"
    assert "power_max_kw" in src16, "picco di potenza non registrato nella sessione"
    ok("AC/DC dalla potenza + statistiche ricariche esposte")
except Exception as e:
    bad(f"AC/DC ricariche: {e}")

print("\n[17] Pannello: stato espansione, consumi/temperatura, descrizione ricarica")
try:
    js = open(os.path.join(CC, "www", "renault-ev-center-panel.js"), encoding="utf-8").read()
    # lo storico mensile non deve riaprirsi da solo al re-render
    assert "_mesiOpen" in js, "storico mensile senza memoria di espansione (si riapre da solo)"
    assert 'details[data-mk]' in js, "manca il listener di stato sui <details> dello storico mensile"
    # grafico consumi vs temperatura
    assert 'id="tempchart"' in js and "_drawTempChart" in js, "manca il grafico consumi/temperatura"
    # descrizione ricarica manuale
    assert 'data-mc="descrizione"' in js, "manca il campo Descrizione nella ricarica manuale"
    src = open(os.path.join(CC, "coordinator.py"), encoding="utf-8").read()
    assert '"consumi_temp": consumi_temp' in src, "consumi_temp non esposto nei dati"
    assert 'descrizione: str = ""' in src, "add_manual_charge non accetta la descrizione"
    flow = open(os.path.join(CC, "__init__.py"), encoding="utf-8").read()
    assert 'vol.Optional("descrizione"' in flow, "schema servizio senza descrizione"
    ok("storico mensile stabile · tempchart · descrizione ricarica · consumi_temp")
except Exception as e:
    bad(f"pannello/storico: {e}")

print("\n[18] Risparmi: confronto termica/elettrica dai record")
try:
    src = open(os.path.join(CC, "coordinator.py"), encoding="utf-8").read()
    for chiave in ('savings["termica"] = {', 'savings["elettrica"] = {',
                   'savings["differenza"] =', 'savings["fv_eur"] ='):
        assert chiave in src, f"manca {chiave}"
    # i costi del periodo NON devono più usare i meter live
    assert 'costo_elet = _f(self.cost_meters' not in src, \
        "il risparmio per periodo usa ancora i meter live (restano a 0)"
    assert 'def _chg_cost(' in src, "manca _chg_cost: costo ricariche dai record"
    assert 'def _periodo(' in src, "manca _periodo: km con ripiego sui viaggi"
    # ricariche dichiarate prima dell'installazione
    assert 'CONF_PRE_KWH' in src and 'CONF_PRE_EUR' in src, "mancano i valori pre-installazione"
    assert 'ricariche_pre' in src, "il valore pre-installazione non è esposto separatamente"
    # i valori dichiarati devono entrare anche nei totali ufficiali (sensore Risparmio Totale)
    assert 'savings["elettrico_totale"] = round(ric_reg + pre_eur, 2)' in src, \
        "il valore dichiarato non entra nel totale ufficiale: Risparmi incoerenti"
    # base odometro all'installazione e confronto "da installazione"
    assert 'savings["da_installazione"]' in src, "manca il confronto da installazione"
    st = open(os.path.join(CC, "store.py"), encoding="utf-8").read()
    assert '"install"' in st and 'install' in st, "la base odometro non è persistita"
    sen = open(os.path.join(CC, "sensor.py"), encoding="utf-8").read()
    assert 'return savings' in sen, "il sensore risparmio non espone il dettaglio completo"
    ok("risparmi: termica/elettrica + differenza + FV in €, costi dai record")
except Exception as e:
    bad(f"risparmi: {e}")

print("\n[19] Peso sul database (recorder)")
try:
    sen = open(os.path.join(CC, "sensor.py"), encoding="utf-8").read()
    assert "_unrecorded_attributes" in sen, (
        "nessuna esclusione dal recorder: gli archivi grandi (fino a ~650 KB) "
        "finiscono nel database a ogni aggiornamento"
    )
    for chiave in ("trips", "days", "mesi", "consumi_temp", "items", "report"):
        assert f'"{chiave}"' in sen, f"{chiave} non escluso dal recorder"
    ok("attributi grandi esclusi dal recorder (restano solo per la UI)")
except Exception as e:
    bad(f"peso database: {e}")

print("\n[20] Automazioni: entita', date e schedulazioni")
try:
    src = open(os.path.join(CC, "coordinator.py"), encoding="utf-8").read()
    # il trigger della fine ricarica deve usare il NOSTRO binary_sensor (sempre on/off)
    assert 'charging = f"binary_sensor.{n}_in_carica"' in src, \
        "il trigger fine ricarica usa l'entità sorgente (può essere testuale: non scatterebbe)"
    # niente condizione sulla data: scartava le ricariche notturne
    assert "state_attr('sensor.\" + n + \"_ultima_ricarica', 'data') == now()" not in src, \
        "la fine ricarica ha ancora la condizione sulla data (ricariche notturne perse)"
    # date gg-mm-aaaa nelle notifiche
    assert "%d-%m-%Y" in src, "le date nelle notifiche non sono gg-mm-aaaa"
    # schedulazioni persistite
    assert 'setdefault("schedule", {})[tipo]' in src, "le schedulazioni non vengono salvate"
    assert '"schedule": dict(self.store.data' in src, "le schedulazioni non sono esposte nei dati"
    sen = open(os.path.join(CC, "sensor.py"), encoding="utf-8").read()
    assert "class Programmazione(" in sen, "manca il sensore Programmazione"
    st = open(os.path.join(CC, "store.py"), encoding="utf-8").read()
    assert '"schedule"' in st, "lo store non persiste le schedulazioni"
    js = open(os.path.join(CC, "www", "renault-ev-center-panel.js"), encoding="utf-8").read()
    assert 'this._ov("wb_stop_switch")' in js, "il tasto stop wallbox usa ancora l'entità sbagliata"
    assert "_schTouched" in js and "_lowTouched" in js, \
        "i campi giorni verrebbero sovrascritti durante la scelta"
    ok("trigger on/off, date gg-mm-aaaa, schedulazioni persistite, stop wallbox corretto")
except Exception as e:
    bad(f"automazioni: {e}")

print("\n[21] Sperimentazione GSE (fasce orarie)")
try:
    from datetime import datetime as _dt21

    with open(os.path.join(CC, "coordinator.py"), encoding="utf-8") as fh:
        tree21 = ast.parse(fh.read())
    fn21 = next(n for n in ast.walk(tree21)
                if isinstance(n, ast.FunctionDef) and n.name == "_gse_limite_kw")
    ns21: dict = {}
    exec(compile(ast.Module(body=[fn21], type_ignores=[]), "<gse>", "exec"), ns21)

    class _Fake:
        gse_domenica = True
        gse_kw_max = 6.0
        gse_kw_ridotta = 3.0
        gse_start = "23:00"
        gse_end = "07:00"
        gse_holiday = ""
        hass = None

    f = ns21["_gse_limite_kw"].__get__(_Fake())
    assert f(_dt21(2026, 9, 20, 12, 0)) == 6.0, "domenica: deve essere piena potenza"   # domenica
    assert f(_dt21(2026, 9, 21, 23, 30)) == 6.0, "feriale in fascia: piena potenza"
    assert f(_dt21(2026, 9, 21, 6, 0)) == 6.0, "feriale dopo mezzanotte: piena potenza"
    assert f(_dt21(2026, 9, 21, 12, 0)) == 3.0, "feriale fuori fascia: potenza ridotta"
    assert f(_dt21(2026, 9, 21, 22, 59)) == 3.0, "un minuto prima della fascia: ridotta"
    src21 = open(os.path.join(CC, "coordinator.py"), encoding="utf-8").read()
    assert 'self._switch_on("gse")' in src21, "lo switch GSE non è controllato"
    assert "class Programmazione(" in open(os.path.join(CC, "sensor.py"), encoding="utf-8").read()
    ok("GSE: domenica 24h, fascia 23–07 piena, fuori fascia ridotta")
except Exception as e:
    bad(f"GSE: {e}")

print("\n[22] Wallbox, stima e scadenze")
try:
    src = open(os.path.join(CC, "coordinator.py"), encoding="utf-8").read()
    # l'automazione 'batteria bassa' non va più creata e va rimossa sempre
    assert "def _legacy(" in src and '"_batteria_bassa"' in src, \
        "l'automazione 'batteria bassa' non viene rimossa"
    # la stima deve usare il SoC della carica programmata quando attiva
    assert '_sc_prog = (self.store.data.get("schedule"' in src, \
        "la stima ricarica ignora il SoC dell'automazione (due valori diversi)"
    # tagliando: niente doppione km + consegna
    assert 's["nome"] != "Tagliando"' in src, "tagliando duplicato (km + consegna)"
    # stop carica: usa lo stop dedicato e rispetta il SoC obiettivo anche in modalità orario
    assert "self.wb_stop_switch" in src, "lo stop carica non usa l'entità di stop dedicata"
    assert "target_ent = ent if avvia else" in src, "il fermo carica ripiega sull'avvio"
    assert "battery >= stop_target" in src, "in modalità orario il SoC obiettivo viene ignorato"
    # una sola notifica di fine carica (l'automazione), con la posizione
    assert 'Notifica fine ricarica nativa rimossa' not in src
    assert '"zona": self._zone_label(' in src, "la ricarica non salva la posizione"
    assert "finished.get('soc_start')" not in src, \
        "la notifica di fine carica è ancora inviata due volte (nativa + automazione)"
    assert "'zona') or '—'" in src, "la notifica di fine carica non include la posizione"
    # programmazione: l'orario mostrato in Panoramica viene dalla programmazione salvata
    assert "_pg.attributes.schedule.ricarica" in open(
        os.path.join(CC, "www", "renault-ev-center-panel.js"), encoding="utf-8").read(), \
        "Panoramica: 'Carica programmata' non legge l'orario dell'automazione"
    # FONTE UNICA del prezzo carburante (prima: coordinator da config, pannello da localStorage)
    assert '_setting_num("fuel_price"' in src, "il prezzo carburante non usa il number dell'integrazione"
    num = open(os.path.join(CC, "number.py"), encoding="utf-8").read()
    assert '("fuel_price"' in num, "manca il number Prezzo Carburante"
    js2 = open(os.path.join(CC, "www", "renault-ev-center-panel.js"), encoding="utf-8").read()
    assert 'this._num(this._nid("prezzo_carburante"))' in js2, \
        "il pannello non legge il prezzo carburante dall'entità (usa ancora localStorage)"
    assert 'localStorage.getItem("rec_diesel")' not in js2.split("_dieselPrice", 1)[0], \
        "il pannello ha ancora il vecchio prezzo diesel come fonte primaria"
    # il sensore Programmazione deve leggere lo store (dati sempre freschi)
    sen2 = open(os.path.join(CC, "sensor.py"), encoding="utf-8").read()
    assert 'coordinator.store.data.get("schedule")' in sen2, \
        "Programmazione legge dati vecchi: il form si resetta dopo il salvataggio"
    # gomme: il valore impostato è l'ULTIMO CAMBIO, l'obiettivo si calcola aggiungendo l'intervallo
    assert "last_change=" in src and "kmv = _f(kmv) + interval_km" in src, \
        "gomme: la scadenza non somma l'intervallo all'ultimo cambio"
    assert '_due("Cambio gomme", "gomme", self.tyre_interval, last_change=True)' in src, \
        "il calcolo gomme non è marcato come 'ultimo cambio'"
    js = open(os.path.join(CC, "www", "renault-ev-center-panel.js"), encoding="utf-8").read()
    assert "_findState(" in js, "wallbox: corrente/tensione/temperatura senza ricerca per nome"
    assert 'live.textContent = `${S._fmt(amps, 0)} A`' in js, "lo slider ampere non mostra il valore"
    assert "return x * 1000;" in js, "il grafico wallbox non converte kW → W (resta invisibile)"
    assert "max: 7000" not in js, "il grafico wallbox ha ancora il massimo fisso"
    assert "#22c55e,#16a34a" in js and "#ef4444,#b91c1c" in js, \
        "i tasti Avvia/Ferma wallbox non sono verde/rosso grandi"
    ok("batteria bassa rimossa, stima col SoC programmato, tagliando unico, wallbox a posto")
except Exception as e:
    bad(f"wallbox/stima: {e}")

print("\n[23] Profili di installazione (base / pro / enterprise)")
try:
    flow = open(os.path.join(CC, "config_flow.py"), encoding="utf-8").read()
    assert "async def async_step_user" in flow and "async def async_step_car" in flow, \
        "manca il passo profilo / la schermata auto"
    assert "PROFILE_BASE" in flow and "PROFILE_ENTERPRISE" in flow, "profili non usati nel wizard"
    assert 'if profile != PROFILE_BASE:' in flow, "la sezione GSE non è legata al profilo"
    assert 'if profile == PROFILE_ENTERPRISE:' in flow, "la sezione fotovoltaico non è solo enterprise"
    assert 'self._data[CONF_WALLBOX_ENABLED] = prof != PROFILE_BASE' in flow, \
        "il profilo base non disattiva la wallbox"
    dash = open(os.path.join(CC, "dashboard.py"), encoding="utf-8").read()
    assert '"wallbox": bool(opts_wb)' in dash and '"profile": opts_profile' in dash, \
        "la card non riceve profilo/wallbox: il pannello non può nascondere la pagina"
    js = open(os.path.join(CC, "www", "renault-ev-center-panel.js"), encoding="utf-8").read()
    assert "_navItems()" in js and "_pages()" in js, "il pannello non filtra le pagine"
    assert 'id === "p11"' in js, "la pagina Wallbox non è nascosta col profilo base"
    # scadenze: km mancanti (gomme) invece dei soli giorni + mappa alta come il grafico
    assert "haKm" in js, "le scadenze non mostrano i km mancanti (cambio gomme)"
    assert "grid-auto-rows:330px" in js, "la mappa non ha la stessa altezza del grafico a fianco"
    tr = json.load(open(os.path.join(CC, "strings.json"), encoding="utf-8"))
    assert "car" in tr["config"]["step"] and "user" in tr["config"]["step"], \
        "traduzioni: mancano gli step car/user"
    assert "profile" in tr.get("selector", {}), "traduzioni: manca selector.profile"
    ok("profili base/pro/enterprise: wizard, sezioni, pagina Wallbox e traduzioni")
except Exception as e:
    bad(f"profili: {e}")

print("\n[24] Bilanciamento casa (consumo contatore)")
try:
    cst = open(os.path.join(CC, "const.py"), encoding="utf-8").read()
    for k in ("CONF_HOME_POWER_SENSOR", "CONF_HOME_METER_KW",
              "CONF_HOME_MAX_AMPS", "CONF_HOME_REDUCE_AMPS", "HOME_METER_OPTIONS"):
        assert k in cst, f"const mancante: {k}"
    sw = open(os.path.join(CC, "switch.py"), encoding="utf-8").read()
    assert '"home_balance"' in sw and "Bilanciamento Casa" in sw, "switch bilanciamento casa assente"
    src = open(os.path.join(CC, "coordinator.py"), encoding="utf-8").read()
    assert "async def _home_balance" in src, "manca _home_balance"
    assert "self._switch_on(\"home_balance\")" in src, "lo switch casa non è controllato"
    assert "await self._home_balance(wb_state)" in src, "_home_balance non è chiamato nel ciclo"
    assert "self.home_meter_kw * 1000.0" in src and "hi * 0.8" in src, \
        "soglie non derivate dal contatore (alta = contatore, bassa = 80%)"
    assert ">= 600" in src and ">= 900" in src, "isteresi 10 min / 15 min mancante"
    flow = open(os.path.join(CC, "config_flow.py"), encoding="utf-8").read()
    assert "CONF_HOME_POWER_SENSOR" in flow and '"home"' in flow, \
        "la sezione Bilanciamento casa non è nel config flow"
    js = open(os.path.join(CC, "www", "renault-ev-center-panel.js"), encoding="utf-8").read()
    assert 'data-sw="sw_home"' in js, "switch casa assente nel pannello"
    assert 'case "sw_home": return S._swid("bilanciamento_casa")' in js, \
        "il pannello non mappa lo switch casa"
    assert 'data-wb="home_w"' in js and 'data-wb="home_hi"' in js, \
        "il pannello non mostra consumo/soglia casa"
    for fn in ("strings.json", "translations/it.json", "translations/en.json", "translations/fr.json"):
        t = json.load(open(os.path.join(CC, fn), encoding="utf-8"))
        secs = t["config"]["step"]["wallbox"]["sections"]
        assert "home" in secs and "home_power_sensor" in secs["home"]["data"], \
            f"{fn}: manca la sezione Bilanciamento casa"
    ok("bilanciamento casa: switch, soglie da contatore, isteresi, pannello e traduzioni")
except Exception as e:
    bad(f"bilanciamento casa: {e}")

# ---------------------------------------------------------------- esito
print("\n" + "=" * 62)
if problemi:
    print(f"PROBLEMI: {len(problemi)}  → correggi quanto sopra e rilancia lo script")
    for p in problemi:
        print("  -", p)
    print("Riprendi il lavoro seguendo agent.md sezione 3 e 4.")
    sys.exit(1)
print(f"TUTTO OK ({len(done)} controlli superati). Progetto pronto per test/pubblicazione.")
