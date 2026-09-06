/**
 * Renault EV Center Panel
 * =======================
 * Plancia custom stile "LeapMotor": replica preview/index.html con dati reali.
 * Una sola card full-width (vista "panel"), 10 pagine, palette Renault,
 * binding su entità dell'integrazione + entità auto Renault core.
 *
 * ponytail: binding per nome entità derivato da slug(friendly_name) con
 * candidate multipli per campo; dove lo schema attributi cambia nelle
 * prossime versioni HA, i valori mostrano "—" invece di rompersi.
 * Override puntuali: config.overrides = { chiave: "sensor.xyz" }.
 *
 * Config:
 *   type: custom:renault-ev-center-panel
 *   name: Megane          # nome auto (prefisso entità integrazione)
 *   car: megane           # slug entità Renault core (battery, range, odometer, location)
 *   image: /local/renault-ev-center/auto.png
 *   notify: notify.michele
 *   overrides: {battery: "sensor.megane_battery", ...}
 */
class RenaultEvCenterPanel extends HTMLElement {
  setConfig(config) {
    if (!config) config = {};
    const name = config.name || "Megane";
    this._cfg = {
      name,
      car: config.car || this._slug(name),
      image: config.image || "/local/renault-ev-center/auto.png",
      notify: config.notify || "",
      overrides: config.overrides || {},
      capacity: config.capacity || 60,
    };
    this._page = localStorage.getItem("rec_panel_page") || "p1";
    this._theme = localStorage.getItem("rec_panel_theme") || "blu";
    this._built = false;
    this._raf = null;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    else if (!this._raf) this._raf = requestAnimationFrame(() => { this._raf = null; if (!PAGES[this._page]) this._page = "p1"; this._update(); });
  }

  getCardSize() { return 12; }

  // ------------------------------------------------------------- helpers
  _slug(s) {
    return String(s).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  }
  _ov(k) { return this._cfg.overrides[k]; }
  /** primo stato definito tra candidati */
  _st(...cands) {
    for (const c of cands) {
      const id = typeof c === "string" ? c : null;
      if (!id) continue;
      const s = this._hass.states[id];
      if (s && s.state !== "unavailable" && s.state !== "unknown") return s;
    }
    return null;
  }
  _num(...cands) {
    const s = this._st(...cands);
    if (!s) return null;
    const v = parseFloat(String(s.state).replace(",", "."));
    return isNaN(v) ? null : v;
  }
  _attrAny(state, keys) {
    if (!state || !state.attributes) return null;
    const norm = (k) => this._slug(k);
    const map = {};
    for (const [k, v] of Object.entries(state.attributes)) map[norm(k)] = v;
    for (const k of keys) { const v = map[norm(k)]; if (v !== undefined && v !== null) return v; }
    return null;
  }
  _list(...cands) {
    const s = this._st(...cands);
    const v = s ? this._attrAny(s, ["list", "items", "viaggi", "ricariche", "data", "rows"]) : null;
    return Array.isArray(v) ? v : [];
  }
  _fmt(v, dec = 1) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return v.toLocaleString("it-IT", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }
  _i(v) { return v === null || v === undefined || isNaN(v) ? "—" : Math.round(v).toLocaleString("it-IT"); }

  /** id entità integrazione: sensor.<slug>_<rest> */
  _sid(rest) { return `sensor.${this._slug(this._cfg.name)}_${rest}`; }
  _nid(rest) { return `number.${this._slug(this._cfg.name)}_${rest}`; }
  _bid(rest) { return `binary_sensor.${this._slug(this._cfg.name)}_${rest}`; }
  _swid(rest) { return `switch.${this._slug(this._cfg.name)}_${rest}`; }
  _tid(rest) { return `time.${this._slug(this._cfg.name)}_${rest}`; }
  _selid(rest) { return `select.${this._slug(this._cfg.name)}_${rest}`; }
  _car(dom, rest) { return `${dom}.${this._slug(this._cfg.car)}${rest ? "_" + rest : ""}`; }

  /** chiamata servizio con toast di conferma */
  _call(domain, service, data, msg) {
    this._hass.callService(domain, service, data || {});
    this._toast(msg || `✅ ${domain}.${service} inviato`);
  }
  _toast(text) {
    const t = this.shadowRoot.getElementById("toast");
    if (!t) return;
    t.textContent = text;
    t.classList.add("show");
    clearTimeout(this._toastT);
    this._toastT = setTimeout(() => t.classList.remove("show"), 2600);
  }

  // ------------------------------------------------------------- campi dati
  _field(k) {
    const n = this._slug(this._cfg.name);
    const c = this._cfg.car;
    const S = this;
    switch (k) {
      // Panoramica
      case "batt": return S._ov("battery") ? S._num(S._ov("battery")) : S._num(S._car("sensor", "battery"), S._car("sensor", "battery_level"));
      case "range": return S._ov("range") ? S._num(S._ov("range")) : S._num(S._car("sensor", "range_electric"), S._car("sensor", "battery_autonomy"));
      case "odo": return S._ov("odometer") ? S._num(S._ov("odometer")) : S._num(S._car("sensor", "odometer"));
      case "loc": {
        const s = S._ov("location") ? S._hass.states[S._ov("location")] : S._hass.states[S._car("device_tracker", "location")];
        return s ? (s.attributes.friendly_name || s.state) : null;
      }
      case "charging": return (S._ov("charging") ? S._hass.states[S._ov("charging")] : S._hass.states[S._bid("in_carica")]);
      case "plug": return S._hass.states[S._car("binary_sensor", "plug_status")] || S._hass.states[S._car("binary_sensor", "plugged_in")];
      case "batt_kwh": return S._num(S._sid("batteria_kwh_disponibili"));
      case "km_oggi": return S._num(S._sid("km_giornalieri"), S._sid("km_oggi_trip"));
      case "km_per_kwh": return S._num(S._sid("km_per_kwh"));
      case "kwh_100": return S._num(S._sid("kwh_per_100km"));
      case "kwh_tot": return S._num(S._sid("kwh_totali_consumati"));
      case "costo_km": return S._num(S._sid("costo_per_km"));
      case "costo_100": return S._num(S._sid("costo_per_100_km"));
      case "risp_tot": { const t = S._spesaTeo(S._num(S._ov("odometer"), S._car("sensor", "odometer"))); const c = S._num(S._sid("costo_ricarica_totale")); return (t === null || c === null) ? null : t - c; }
      case "trip_attivo": return S._st(S._sid("trip_attivo"));
      // Ultima ricarica / ricariche
      case "ultima": return S._st(S._sid("ultima_ricarica"));
      case "kwh_oggi_wb": return S._num(S._sid("energia_caricata_giornaliera"), S._sid("wb_energy_oggi"), S._sid("ricariche_oggi"));
      case "kwh_sett_wb": return S._num(S._sid("energia_caricata_settimanale"), S._sid("wb_energy_settimana"), S._sid("ricariche_settimana"));
      case "kwh_mese_wb": return S._num(S._sid("energia_caricata_mensile"), S._sid("wb_energy_mese"), S._sid("ricariche_mese"));
      case "kwh_anno_wb": return S._num(S._sid("energia_caricata_annuale"), S._sid("wb_energy_anno"), S._sid("ricariche_anno"));
      case "costo_oggi": return S._num(S._sid("costo_ricarica_giornaliero"), S._sid("costo_ricarica_oggi"));
      case "costo_sett": return S._num(S._sid("costo_ricarica_settimanale"), S._sid("costo_ricarica_settimana"));
      case "costo_mese": return S._num(S._sid("costo_ricarica_mensile"), S._sid("costo_ricarica_mese"));
      case "costo_anno": return S._num(S._sid("costo_ricarica_annuale"), S._sid("costo_ricarica_anno"));
      case "lista_ric": return S._list(S._sid("lista_ricariche"));
      case "wb_potenza": return S._num(S._sid("wallbox_potenza"));
      case "tipo_ric": return S._st(S._sid("tipo_ricarica_attuale"));
      case "tempo_ric": return S._st(S._sid("tempo_ricarica_stimato"));
      case "ora_compl": return S._st(S._sid("ora_completamento_ricarica"));
      case "costo_corr": return S._num(S._sid("costo_ricarica_corrente_stimato"));
      // Statistiche
      case "stats": return S._st(S._sid("statistiche_viaggi"));
      case "percorrenza": return S._st(S._sid("percorrenza"));
      case "storico": return S._list(S._sid("storico_giornaliero"));
      case "energia_casa": return S._num(S._sid("energia_caricata_casa_totale"));
      case "fv_tot": return S._num(S._sid("energia_caricata_fotovoltaico_totale"));
      case "fv_mese": return S._num(S._sid("ricaricato_fotovoltaico_mese"));
      // Salute
      case "soh_off": return S._num(S._nid("soh_ufficiale"));
      case "soh_est": return S._num(S._sid("soh_stimato"));
      case "kwh_1pct": return S._num(S._sid("kwh_per_1_batteria"), S._sid("kwh_per_1pct"));
      case "eff_ric": return S._num(S._sid("efficienza_ricarica"));
      case "perdite": return S._st(S._sid("perdite_ultima_ricarica"));
      case "batt_ult": return S._num(S._sid("energia_batteria_ultima_ricarica"));
      case "rete_ult": return S._num(S._sid("energia_rete_ultima_ricarica"), S._sid("kwh_ultima_ricarica"), S._sid("ultima_ricarica"));
      // Manutenzione
      case "tagliandi": return S._st(S._sid("tagliandi"));
      case "assic": return S._st(S._sid("assicurazione"));
      case "scadenze": return S._st(S._sid("prossima_scadenza"));
      case "risp_tagliandi": return S._num(S._sid("risparmio_tagliandi"));
      case "risp_bollo": return S._num(S._sid("risparmio_bollo"));
      case "assic_costo": return S._num(S._nid("assic_costo"), S._nid("costo_assicurazione"));
      // Risparmi carburante (calcolati client: le entità risparmio_* non esistono nell'integrazione)
      case "risp_mese": return S._rispKm(S._num(S._sid("km_mensili")), S._num(S._sid("costo_ricarica_mensile"), S._sid("costo_ricarica_mese")));
      case "risp_anno": return S._rispKm(S._num(S._sid("km_annuali")), S._num(S._sid("costo_ricarica_annuale"), S._sid("costo_ricarica_anno")));
      case "spesa_teorica": return S._ov("spesa_teorica") ? S._num(S._ov("spesa_teorica")) : S._spesaTeo(S._num(S._ov("odometer"), S._car("sensor", "odometer")));
      case "costo_ric_tot": return S._num(S._sid("costo_ricarica_totale"), S._ov("costo_ric_tot"));
      // Extra
      case "drain": return S._num(S._sid("batteria_persa_da_fermo_oggi"));
      case "co2": return S._st(S._sid("co2_risparmiata"));
      case "zona": return S._list(S._sid("consumo_per_zona"));
      case "topstop": return S._st(S._sid("viaggio_top_stop_del_mese"), S._sid("viaggio_top_stop"));
      // Extra p1/p10
      case "name": return S._cfg.name;
      case "notify": return S._cfg.notify || "da configurare";
      case "diesel": {
        const s = S._ov("diesel_price") ? S._hass.states[S._ov("diesel_price")] : null;
        return s ? s.state : (localStorage.getItem("rec_diesel") || "1.72");
      }
      // Impostazioni (entità di configurazione)
      case "n_price_home": return S._nid("costo_energia_casa");
      case "n_price_public": return S._nid("costo_colonnina");
      case "n_price_solar": return S._nid("costo_fotovoltaico");
      case "n_capacity": return S._nid("capacita_batteria");
      case "n_target": return S._nid("obiettivo_ricarica");
      case "n_soh": return S._nid("soh_ufficiale");
      case "n_assic": return S._nid("costo_assicurazione");
      case "n_prio": return S._nid("priorita_batteria_casa");
      case "sw_start": return S._swid("notifica_avvio_ricarica");
      case "sw_end": return S._swid("notifica_fine_ricarica");
      case "sw_low": return S._swid("promemoria_batteria_bassa");
      case "sw_sched": return S._swid("carica_programmata");
      case "sw_bal": return S._swid("bilanciamento_solare");
      case "t_start": return S._tid("carica_orario_avvio");
      case "t_stop": return S._tid("carica_orario_stop");
      case "t_low_start": return S._tid("promemoria_inizio");
      case "t_low_end": return S._tid("promemoria_fine");
      case "sel_tipo": return S._selid("filtro_tipo_ricarica");
      case "sel_periodo": return S._selid("filtro_periodo_ricariche");
      case "sel_anno": return S._selid("filtro_anno_ricariche");
      default: return null;
    }
  }
  _f(k) { const v = this._field(k); return v === null || v === undefined ? "—" : v; }
  _on(k) { const s = this._field(k); return s && s.state === "on"; }
  /** prezzo diesel €/l: overrides.diesel_price (sensore live) → localStorage rec_diesel → default */
  _dieselPrice() {
    const s = this._ov("diesel_price") ? this._hass.states[this._ov("diesel_price")] : null;
    const v = s ? parseFloat(s.state) : NaN;
    if (!isNaN(v)) return v;
    const ls = parseFloat(localStorage.getItem("rec_diesel"));
    return isNaN(ls) ? 1.72 : ls;
  }
  _spesaTeo(km) {
    if (km === null) return null;
    // ponytail: equivalenza fissa 6 l/100km diesel, configurabile via overrides.diesel_l100
    const l100 = parseFloat(this._cfg.overrides.diesel_l100) || 6;
    return km / 100 * l100 * this._dieselPrice();
  }
  /** risparmio = spesa teorica su quei km − costo ricarica periodo */
  _rispKm(km, costo) {
    if (km === null || km === undefined || costo === null || costo === undefined) return null;
    return this._spesaTeo(km) - costo;
  }

  // ------------------------------------------------------------- costruzione DOM
  _build() {
    this._built = true;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const c = this._cfg;
    this.shadowRoot.innerHTML = `
    <style>${CSS}</style>
    <div class="app" data-theme="${this._theme}">
      <div class="sidebar">
        <div class="logo">
          <div class="ph">🚗</div>
          <div><b>Renault EV<br>Center</b><span class="ver">v1.0.3.5</span><small>${c.name} · live</small></div>
        </div>
        <div class="nav" id="nav">
          ${NAV.map(([id, em, label]) => `<button data-p="${id}" class="${id === this._page ? "active" : ""}"><span class="em">${em}</span> ${label}</button>`).join("")}
        </div>
        <div class="themes">
          <p>Palette</p>
          ${THEMES.map(([id, dot, label]) => `<button data-t="${id}" class="${id === this._theme ? "active" : ""}"><span class="sw" style="background:${dot}"></span> ${label}</button>`).join("")}
        </div>
      </div>
      <div class="mobilenav" id="mnav">
        ${NAV.map(([id, em, label]) => `<button data-p="${id}" class="${id === this._page ? "active" : ""}"><span class="em">${em}</span> ${label}</button>`).join("")}
      </div>
      <div class="main">${Object.entries(PAGES).map(([id, html]) => `<section id="${id}" class="page ${id === this._page ? "active" : ""}">${html}</section>`).join("")}
      </div>
    </div>
    <div id="toast"></div>`;
    // nav + temi
    const gotoHandler = (ev) => {
      const b = ev.target.closest("button[data-p]");
      if (!b) return;
      this._goto(b.dataset.p);
    };
    this.shadowRoot.getElementById("nav").addEventListener("click", gotoHandler);
    this.shadowRoot.getElementById("mnav").addEventListener("click", gotoHandler);
    this.shadowRoot.querySelectorAll(".themes button").forEach((b) => {
      b.addEventListener("click", () => this._theme_(b.dataset.t));
    });
    // comandi / bottoni
    this.shadowRoot.querySelectorAll("[data-cmd]").forEach((el) => {
      el.addEventListener("click", () => this._cmd(el.dataset.cmd, el));
    });
    // input number: risolvi entità dal mapping PRIMA di attaccare i listener
    this.shadowRoot.querySelectorAll("input[data-n]").forEach((inp) => { if (!inp.dataset.ent) inp.dataset.ent = this._field(inp.dataset.n); });
    this.shadowRoot.querySelectorAll("input[data-ent]").forEach((inp) => {
      inp.addEventListener("change", () => {
        const v = parseFloat(inp.value.replace(",", "."));
        if (isNaN(v)) return;
        const eid = inp.dataset.ent || this._field(inp.dataset.n);
        if (!eid || typeof eid !== "string") return;
        this._call("number", "set_value", { entity_id: eid, value: v });
      });
    });
    // switch/number live-bind: popola data-ent al primo update
    this.shadowRoot.querySelectorAll("[data-sw]").forEach((el) => { el.dataset.ent = this._field(el.dataset.sw); });
    // toggle switch stile v13: input dentro label → change, non click
    this.shadowRoot.querySelectorAll("input[data-sw]").forEach((inp) => {
      inp.dataset.ent = this._field(inp.dataset.sw);
      inp.addEventListener("change", () => {
        const eid = inp.dataset.ent;
        if (!eid) return;
        this._call("homeassistant", inp.checked ? "turn_on" : "turn_off", { entity_id: eid });
      });
    });
    this.shadowRoot.querySelectorAll("input[data-n]").forEach((inp) => { inp.dataset.ent = this._field(inp.dataset.n); });
    // input locali (localStorage): prezzo diesel, consumo equivalente, notify, preavviso
    this.shadowRoot.querySelectorAll("input[data-ls]").forEach((inp) => {
      const saved = localStorage.getItem(inp.dataset.ls);
      if (saved !== null && saved !== "") inp.value = saved;
      inp.addEventListener("change", () => { localStorage.setItem(inp.dataset.ls, inp.value); this._update(); });
    });
    // notify salvato localmente → config runtime se non impostato in YAML
    if (!this._cfg.notify) { const nn = localStorage.getItem("rec_notify"); if (nn) this._cfg.notify = nn; }
    this._update();
  }
  _goto(p) {
    this._page = p;
    localStorage.setItem("rec_panel_page", p);
    this.shadowRoot.querySelectorAll(".nav button, .mobilenav button").forEach((b) => b.classList.toggle("active", b.dataset.p === p));
    this.shadowRoot.querySelectorAll(".page").forEach((s) => s.classList.toggle("active", s.id === p));
  }
  _theme_(t) {
    this._theme = t;
    localStorage.setItem("rec_panel_theme", t);
    this.shadowRoot.querySelector(".app").dataset.theme = t;
    this.shadowRoot.querySelectorAll(".themes button").forEach((b) => b.classList.toggle("active", b.dataset.t === t));
  }
  _cmd(cmd, el) {
    const n = this._slug(this._cfg.name);
    const D = "renault_ev_center";
    switch (cmd) {
      case "ac": {
        const cl = this._st(this._car("climate", ""), this._ov("climate"));
        if (cl) this._call("climate", "set_temperature", { entity_id: cl.entity_id, temperature: 21 }, "❄️ A/C: 21 °C");
        else this._toast("⚠️ Nessun climate dell'auto trovato");
        break;
      }
      case "charge": {
        const b = this._st(this._car("button", "start_charge"), this._ov("start_charge"));
        if (b) this._call("button", "press", { entity_id: b.entity_id }, "⚡ Avvio carica");
        else this._toast("⚠️ Pulsante carica non trovato (configura overrides.start_charge)");
        break;
      }
      case "close_trip": this._call(D, "close_trip", {}, "🏁 Viaggio chiuso"); break;
      case "csv": this._call(D, "export_trips_csv", {}, "📥 CSV esportato"); break;
      case "create_automations": this._call(D, "create_automations", {}, "✨ Automazioni create"); break;
      case "reset_km": this._call(D, "reset_counters", { scope: "km" }, "🔄 Km azzerati"); break;
      case "reset_energia": this._call(D, "reset_counters", { scope: "energia" }, "🔄 Energia azzerata"); break;
      case "reset_costi": this._call(D, "reset_counters", { scope: "costi" }, "🔄 Costi azzerati"); break;
      case "ass_plus6": this._call(D, "renew_insurance", { mesi: 6 }, "🛡️ Rinnovata +6 mesi"); break;
      case "ass_plus12": this._call(D, "renew_insurance", { mesi: 12 }, "🛡️ Rinnovata +1 anno"); break;
      case "switch": {
        const eid = el.dataset.ent;
        const s = this._hass.states[eid];
        if (!s) return;
        this._call("homeassistant", s.state === "on" ? "turn_off" : "turn_on", { entity_id: eid });
        break;
      }
    }
  }

  // ------------------------------------------------------------- aggiornamento valori
  _update() {
    const root = this.shadowRoot;
    // barra batteria
    const b = this._num(this._ov("battery"), this._car("sensor", "battery"), this._car("sensor", "battery_level"));
    const bar = root.querySelector('[data-b="battbar"]');
    if (bar) {
      bar.style.width = `${b === null ? 0 : Math.min(100, Math.max(0, b))}%`;
      bar.style.background = b === null ? "var(--line)" : b < 20 ? "var(--bad)" : b < 45 ? "var(--warn)" : "var(--accent)";
    }
    root.querySelectorAll("[data-f]").forEach((el) => {
      if (el.tagName === "INPUT") return; // gli input data-ls si inizializzano in _build
      const k = el.dataset.f;
      const v = this._f(k);
      if (typeof v === "object") el.textContent = v.state ?? "—";
      else el.textContent = String(v);
    });
    root.querySelectorAll("[data-sw]").forEach((el) => {
      if (el.tagName === "INPUT") { const s = this._hass.states[el.dataset.ent]; el.checked = !!s && s.state === "on"; }
    });
    // chips stato
    const chipLoc = root.querySelector('[data-c="loc"]');
    if (chipLoc) chipLoc.textContent = `📍 ${this._f("loc")}`;
    const chipCh = root.querySelector('[data-c="charging"]');
    if (chipCh) {
      const on = this._on("charging");
      chipCh.textContent = on ? "🔌 In carica" : "🔓 Non in carica";
      chipCh.className = `chip ${on ? "ok" : ""}`;
    }
    const chipPlug = root.querySelector('[data-c="plug"]');
    if (chipPlug) {
      const p = this._field("plug");
      const on = p && p.state === "on";
      chipPlug.textContent = on ? "🔗 Collegata" : "🔗 Scollegata";
    }
    // foto auto
    const img = root.querySelector('[data-c="carimg"]');
    if (img) {
      img.innerHTML = this._cfg.image
        ? `<img src="${this._cfg.image}" alt="${this._cfg.name}" onerror="this.parentNode.innerHTML='<div class=\\'ph\\'>🚗</div>'">`
        : `<div class="ph">🚗</div>`;
    }
    // comandi: valori
    const cmdCharge = root.querySelector('[data-v="cmd_charge"]');
    if (cmdCharge) cmdCharge.textContent = this._on("charging") ? "In carica" : "Non in carica";
    const cmdPlug = root.querySelector('[data-v="cmd_plug"]');
    if (cmdPlug) cmdPlug.textContent = this._field("plug") && this._field("plug").state === "on" ? "Collegata" : "Scollegata";
    const cmdTipo = root.querySelector('[data-v="cmd_tipo"]');
    if (cmdTipo) cmdTipo.textContent = this._f("tipo_ric");
    const cmdTempo = root.querySelector('[data-v="cmd_tempo"]');
    if (cmdTempo) cmdTempo.textContent = this._f("tempo_ric");
    const cmdOra = root.querySelector('[data-v="cmd_ora"]');
    if (cmdOra) cmdOra.textContent = this._f("ora_compl");
    const cmdWb = root.querySelector('[data-v="cmd_wb"]');
    if (cmdWb) cmdWb.textContent = this._wb_state_txt();
    // chip switch: ON/OFF
    root.querySelectorAll("[data-sw]").forEach((el) => {
      const s = el.dataset.ent ? this._hass.states[el.dataset.ent] : null;
      if (!s) { el.textContent = "—"; el.className = "chip"; return; }
      const on = s.state === "on";
      el.textContent = on ? "ON" : "OFF";
      el.className = `chip ${on ? "ok" : ""}`;
    });
    // input number: valore corrente
    root.querySelectorAll("input[data-n]").forEach((inp) => {
      if (document.activeElement === inp) return;
      const s = this._hass.states[inp.dataset.ent];
      if (s) inp.value = s.state;
    });
    // righe lista da attributo (consumo_per_zona ecc.)
    root.querySelectorAll("[data-attr-list]").forEach((tb) => {
      const rows = this._list(this._sid(tb.dataset.attrList));
      tb.innerHTML = rows.slice(0, 8).map((r) =>
        `<tr><td>${r.zona ?? r.nome ?? r.rotta ?? "—"}</td><td>${r.viaggi ?? r.n ?? "—"}</td>
        <td>${this._fmt(parseFloat(r.km ?? 0), 1)}</td>
        <td><span class="badge">${this._fmt(parseFloat(r.kwh_100km ?? r.efficienza ?? 0), 1)}</span></td></tr>`).join("")
        || `<tr><td colspan="4" style="color:var(--muted)">Nessun dato</td></tr>`;
    });
    // grafico 7 giorni
    this._drawBars(root.querySelector('[data-c="bars7"]'), this._last7());
    // tabelle dati dinamici
    this._tableViaggi(root);
    this._tableRicariche(root);
    this._tableSalute(root);
    this._treeViaggi(root);
    this._tileStats(root);
    this._rowsAttr(root);
  }
  _wb_state_txt() {
    const s = this._st(this._sid("wallbox_potenza"));
    if (!s) return "—";
    const p = parseFloat(s.state);
    return !isNaN(p) && p > 0 ? `${this._fmt(p, 2)} kW` : "Inattiva";
  }
  _last7() {
    const arr = this._list(this._sid("storico_giornaliero"));
    const out = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date(Date.now() - i * 86400000);
      const key = d.toISOString().slice(0, 10);
      const row = arr.find((r) => String(r.data || r.giorno || r.date || "").startsWith(key));
      const km = row ? parseFloat(row.km ?? row.chilometri ?? 0) || 0 : 0;
      out.push({ label: d.toLocaleDateString("it-IT", { weekday: "narrow" }), km });
    }
    return out;
  }
  _drawBars(box, data) {
    if (!box) return;
    const max = Math.max(1, ...data.map((d) => d.km));
    box.innerHTML = data.map((d) =>
      `<div style="flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:4px">
        <div style="width:100%;background:var(--accent);opacity:.85;border-radius:4px 4px 0 0;height:${d.km > 0 ? Math.round((d.km / max) * 100) : 2}%"></div>
        <span style="font-size:10px;color:var(--muted)">${d.label}</span></div>`).join("");
  }
  _rowsOf(state, keys) {
    const list = this._list(state ? state.entity_id : "");
    return list;
  }
  _tableViaggi(root) {
    const s = this._st(this._sid("viaggi_recenti"));
    const rows = this._list(s ? s.entity_id : "");
    const tb = root.querySelector('[data-c="tab-viaggi"]');
    if (!tb) return;
    tb.innerHTML = rows.slice(0, 8).map((r) => {
      const eff = r.efficienza ?? r.kwh_100km ?? r.eff;
      return `<tr><td>${r.data ?? "—"}</td><td>${r.ora_inizio ?? "—"}${r.ora_fine ? "–" + r.ora_fine : ""}</td>
        <td><b>${this._fmt(parseFloat(r.km ?? r.chilometri ?? 0), 1)}</b></td>
        <td>${r.delta_soc ?? "—"}</td><td>${this._fmt(parseFloat(r.kwh ?? 0), 2)}</td>
        <td><span class="badge">${this._fmt(parseFloat(eff ?? 0), 1)}</span></td>
        <td>${this._fmt(parseFloat(r.costo ?? 0), 2)} €</td>
        <td>${r.ricarica_precedente ?? r.prima ?? "—"}</td></tr>`;
    }).join("") || `<tr><td colspan="8" style="color:var(--muted)">Nessun viaggio registrato</td></tr>`;
  }
  _tableRicariche(root) {
    const rows = this._list(this._sid("lista_ricariche"));
    const tb = root.querySelector('[data-c="tab-ricariche"]');
    if (!tb) return;
    tb.innerHTML = rows.slice(0, 8).map((r) => {
      const dur = r.durata ?? r.durata_h ?? "—";
      return `<tr><td>${r.data ?? "—"}${r.ora_inizio ? " · " + r.ora_inizio : ""}</td>
        <td>${r.tipo ?? "—"}</td><td>${dur}</td>
        <td><b>${r.delta_soc ? "+" + r.delta_soc + "%" : "—"}</b></td>
        <td>${this._fmt(parseFloat(r.kwh ?? r.energia ?? 0), 2)}</td>
        <td>${this._fmt(parseFloat(r.kw_medio ?? r.media ?? 0), 2)}</td>
        <td>${this._fmt(parseFloat(r.costo_kwh ?? 0), 3)}</td>
        <td><b>${this._fmt(parseFloat(r.costo ?? 0), 2)} €</b></td></tr>`;
    }).join("") || `<tr><td colspan="8" style="color:var(--muted)">Nessuna ricarica registrata</td></tr>`;
  }
  _tableSalute(root) {
    const rows = this._list(this._sid("lista_ricariche"));
    const tb = root.querySelector('[data-c="tab-salute"]');
    if (!tb) return;
    tb.innerHTML = rows.slice(0, 6).map((r) => {
      const rete = parseFloat(r.kwh ?? r.energia ?? 0);
      const batt = parseFloat(r.kwh_batteria ?? r.kwh_netto ?? rete * 0.94);
      const eff = rete > 0 ? (batt / rete) * 100 : 0;
      return `<tr><td>${r.data ?? "—"}</td><td>${r.delta_soc ? "+" + r.delta_soc + "%" : "—"}</td>
        <td>${this._fmt(rete, 2)}</td><td>${this._fmt(batt, 2)}</td>
        <td><span class="badge">${this._fmt(eff, 1)}%</span></td></tr>`;
    }).join("") || `<tr><td colspan="5" style="color:var(--muted)">Nessuna sessione</td></tr>`;
  }
  _treeViaggi(root) {
    const box = root.querySelector('[data-c="tree"]');
    if (!box) return;
    const arch = this._st(this._sid("archivio_viaggi"), this._sid("storico_giornaliero"));
    const rows = this._list(arch ? arch.entity_id : "");
    if (!rows.length) { box.innerHTML = `<div style="color:var(--muted)">Archivio viaggi vuoto</div>`; return; }
    // raggruppa per anno → mese
    const tree = {};
    rows.forEach((r) => {
      const d = String(r.data || "");
      const y = d.slice(0, 4) || "—", m = d.slice(5, 7) || "—";
      (tree[y] = tree[y] || {})[m] = (tree[y][m] || []).concat(r);
    });
    box.innerHTML = Object.entries(tree).sort().reverse().slice(0, 1).map(([y, mesi]) => {
      const tot = Object.values(mesi).flat();
      const km = tot.reduce((a, r) => a + (parseFloat(r.km) || 0), 0);
      return `<div class="anno"><b style="font-size:17px">▼ ${y}</b>
        <span style="float:right;color:var(--muted)">${tot.length} viaggi · <b style="color:var(--txt)">${this._i(km)} km</b></span>
        ${Object.entries(mesi).sort().reverse().map(([m, rs]) => {
          const kmM = rs.reduce((a, r) => a + (parseFloat(r.km) || 0), 0);
          return `<div class="mese">▼ ${NOMI_MESI[parseInt(m, 10) - 1] || m} <span style="float:right;color:var(--muted);font-weight:400">${rs.length} viaggi · ${this._i(kmM)} km</span></div>
            ${rs.slice(0, 4).map((r) => `<div class="giorno">• <b>${r.data ?? ""}</b> — ${this._fmt(parseFloat(r.km) || 0, 1)} km <span class="badge">${this._fmt(parseFloat(r.efficienza ?? 0), 1)}</span> · ${this._fmt(parseFloat(r.costo ?? 0), 2)} €</div>`).join("")}`;
        }).join("")}</div>`;
    }).join("");
  }
  _tileStats(root) {
    const s = this._st(this._sid("statistiche_viaggi"));
    if (!s) return;
    const g = (keys) => this._attrAny(s, keys);
    const set = (id, v, dec) => { const el = root.querySelector(`[data-t="${id}"]`); if (el) el.textContent = v; };
    set("tot_viaggi", this._i(parseFloat(g(["viaggi", "totale_viaggi", "n_viaggi"])) || 0));
    set("tot_km", this._i(parseFloat(g(["km", "km_totali", "distanza"])) || 0));
    set("eff_media", this._fmt(parseFloat(g(["efficienza_media", "kwh_100km", "media"])) || 0, 1));
    set("eff_best", this._fmt(parseFloat(g(["efficienza_best", "best", "record"])) || 0, 1));
    set("tempo", this._fmt(parseFloat(g(["tempo_guida", "ore_guida"])) || 0, 0) + " h");
    set("energia", this._i(parseFloat(g(["energia_usata", "kwh_totali"])) || 0));
    set("n_ricariche", this._i(parseFloat(g(["ricariche", "n_ricariche"])) || 0));
    set("energia_caricata", this._i(parseFloat(g(["energia_caricata", "kwh_caricati"])) || 0));
  }
  _rowsAttr(root) {
    // righe generiche: [data-attr="entityKey|attrKeys"] → testo
    root.querySelectorAll("[data-attr]").forEach((el) => {
      const [src, ...keys] = el.dataset.attr.split("|");
      let s = this._field(src);
      if (!(s && s.entity_id)) s = this._st(this._sid(src));
      let v = s ? this._attrAny(s, keys.length ? keys : [src]) : null;
      if (v === null) v = s ? s.state : "—";
      if (typeof v === "object") v = v.value ?? v.testo ?? JSON.stringify(v);
      el.textContent = String(v);
    });
  }

  static getStubConfig() {
    return { name: "Megane", car: "megane", image: "/local/renault-ev-center/auto.png" };
  }
}

const NOMI_MESI = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"];
const NAV = [
  ["p1", "📊", "Panoramica"], ["p2", "🛣️", "Viaggi"], ["p3", "📈", "Statistiche"],
  ["p4", "🔌", "Ricariche"], ["p5", "💚", "Salute batteria"], ["p6", "🔧", "Manutenzione"],
  ["p7", "💰", "Risparmi"], ["p8", "⭐", "Extra"], ["p9", "🤖", "Automazioni"], ["p10", "⚙️", "Impostazioni"],
];
const THEMES = [
  ["blu", "#4d8dff", "🔵 Blu Megane"], ["giallo", "#F5CB39", "🟡 Giallo R5"],
  ["verde", "#57b98a", "🟢 Verde R4"], ["aviation", "#c9d4e2", "⚪ Grigio Aviation"],
];

const CSS = `
.app{background:var(--bg);color:var(--txt);font-family:'Segoe UI',system-ui,sans-serif;transition:background .25s,color .25s}
.app[data-theme="blu"]{--bg:#0d1522;--panel:#14202f;--panel2:#101b2c;--line:#1e2d40;--txt:#e8eef6;--muted:#8296ad;--accent:#4d8dff;--accent-soft:rgba(77,141,255,.15);--good:#4ade80;--warn:#fbbf24;--bad:#f87171}
.app[data-theme="giallo"]{--bg:#141414;--panel:#1d1d1d;--panel2:#181818;--line:#2a2a2a;--txt:#f2f2f2;--muted:#9e9e9e;--accent:#F5CB39;--accent-soft:rgba(245,203,57,.14);--good:#7ed957;--warn:#ff9f43;--bad:#ff5252}
.app[data-theme="verde"]{--bg:#0f1613;--panel:#16211c;--panel2:#121a16;--line:#22322a;--txt:#e9f2ec;--muted:#87a094;--accent:#57b98a;--accent-soft:rgba(87,185,138,.15);--good:#57b98a;--warn:#fbbf24;--bad:#f87171}
.app[data-theme="aviation"]{--bg:#16181c;--panel:#20242b;--panel2:#1a1d23;--line:#2e333c;--txt:#eef1f5;--muted:#9aa4b1;--accent:#c9d4e2;--accent-soft:rgba(201,212,226,.13);--good:#7ed957;--warn:#fbbf24;--bad:#ff6b6b}
*{margin:0;padding:0;box-sizing:border-box}
:host{display:block}
.sidebar{position:absolute;top:0;bottom:0;left:0;width:230px;background:var(--panel2);border-right:1px solid var(--line);padding:18px 12px;overflow-y:auto}
.app{display:flex;min-height:520px;position:relative;overflow:hidden;border-radius:14px}
.main{flex:1;margin-left:230px;padding:24px 28px}
.logo{display:flex;align-items:center;gap:12px;padding:6px 10px 14px}
.logo .ph{font-size:34px}
.logo b{display:block;font-size:15px;line-height:1.15}
.ver{display:inline-block;font-size:10.5px;font-weight:700;color:var(--accent);border:1px solid var(--accent);border-radius:6px;padding:1px 7px;margin-top:4px;letter-spacing:.05em}
.logo small{color:var(--muted);font-size:11px;display:block;margin-top:3px}
.nav{display:flex;flex-direction:column;gap:3px;margin-top:10px}
.nav button{display:flex;align-items:center;gap:10px;background:none;border:none;color:var(--muted);padding:9px 14px;border-radius:10px;font-size:13.5px;cursor:pointer;text-align:left;width:100%}
.nav button:hover{background:var(--accent-soft);color:var(--txt)}
.nav button.active{background:var(--accent-soft);color:var(--accent);font-weight:600}
.nav .em{width:20px;text-align:center}
.themes{margin-top:14px;border-top:1px solid var(--line);padding-top:10px}
.themes p{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin:0 10px 8px}
.themes button{display:flex;align-items:center;gap:8px;width:100%;background:none;border:none;color:var(--muted);padding:6px 10px;border-radius:8px;font-size:13px;cursor:pointer;text-align:left}
.themes button.active{color:var(--txt);background:var(--accent-soft)}
.sw{width:14px;height:14px;border-radius:4px;border:1px solid var(--line);display:inline-block}
h1{font-size:26px;margin-bottom:4px}
.sub{color:var(--muted);font-size:13.5px;margin-bottom:22px}
.page{display:none}.page.active{display:block}
.grid{display:grid;gap:16px}
.g3{grid-template-columns:repeat(3,1fr)}
.g2{grid-template-columns:repeat(2,1fr)}
@media(max-width:1100px){.g3{grid-template-columns:repeat(2,1fr)}}
@media(max-width:700px){.g3,.g2{grid-template-columns:1fr}.sidebar{display:none}.main{margin-left:0}}
.mobilenav{display:none}
.note{margin-top:26px;color:var(--muted);font-size:12.5px;border-top:1px dashed var(--line);padding-top:14px}
.switch{position:relative;width:46px;height:25px;flex-shrink:0;display:inline-block}
.switch input{opacity:0;width:0;height:0}
.switch span{position:absolute;inset:0;background:#39445a;border-radius:999px;transition:.25s;cursor:pointer}
.switch span::before{content:"";position:absolute;width:19px;height:19px;border-radius:50%;background:#fff;top:3px;left:3px;transition:.25s}
.switch input:checked + span{background:var(--accent)}
.switch input:checked + span::before{transform:translateX(21px)}
@media(max-width:700px){
  .mobilenav{display:flex;gap:6px;overflow-x:auto;padding:10px 0 12px;-webkit-overflow-scrolling:touch;scrollbar-width:none}
  .mobilenav::-webkit-scrollbar{display:none}
  .mobilenav button{flex:0 0 auto;display:flex;align-items:center;gap:6px;background:var(--panel2);border:1px solid var(--line);color:var(--muted);padding:8px 12px;border-radius:10px;font-size:12.5px;cursor:pointer;white-space:nowrap}
  .mobilenav .em{font-size:15px}
  .mobilenav button.active{background:var(--accent-soft);border-color:var(--accent);color:var(--accent);font-weight:600}
  .main{padding:14px 14px}
}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}
.card h3{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:12px;font-weight:600}
.big{font-size:44px;font-weight:800;line-height:1}
.big small{font-size:18px;font-weight:600;color:var(--muted)}
.bar{height:9px;background:var(--line);border-radius:6px;margin-top:12px;overflow:hidden}
.bar i{display:block;height:100%;border-radius:6px;background:var(--accent)}
.row{display:flex;justify-content:space-between;font-size:13.5px;padding:7px 0;border-bottom:1px solid var(--line);gap:10px}
.row:last-child{border-bottom:none}
.row span:first-child{color:var(--muted)}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.chip{font-size:12px;padding:5px 11px;border-radius:999px;border:1px solid var(--line);background:var(--panel2)}
.chip.ok{color:var(--good);border-color:var(--good)}
.chip.acc{color:var(--accent);border-color:var(--accent)}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:16px}
@media(max-width:900px){.tiles{grid-template-columns:repeat(2,1fr)}}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;display:flex;gap:13px;align-items:center}
.tile .em{width:42px;height:42px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:21px;background:var(--accent-soft)}
.tile .v{font-size:24px;font-weight:800;line-height:1.05}
.tile .l{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-top:3px}
.cmd{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:13px 8px;text-align:center;font-size:12px;cursor:pointer}
.cmd .em{font-size:22px;display:block;margin-bottom:5px}
.cmd b{display:block;margin-top:2px;font-weight:600}
.cmd:hover{border-color:var(--accent)}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{color:var(--muted);text-align:left;font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;padding:8px 10px;border-bottom:1px solid var(--line)}
td{padding:9px 10px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:none}
.badge{color:var(--accent);background:var(--accent-soft);border-radius:7px;padding:3px 8px;font-size:12px;font-weight:600}
.tree{font-size:14px}
.tree .anno{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin-bottom:12px}
.tree .mese{margin:10px 0 4px 18px;font-weight:700}
.tree .giorno{margin:5px 0 5px 40px;color:var(--muted)}
.tree .giorno b{color:var(--txt)}
select,input{background:var(--panel2);color:var(--txt);border:1px solid var(--line);border-radius:8px;padding:8px 12px;font-size:14px}
.inp{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid var(--line);font-size:14px;gap:10px}
.inp input{width:110px;text-align:right}
.inp .u{color:var(--muted);font-size:12px;width:52px}
.btn{background:var(--panel2);border:1px solid var(--line);color:var(--txt);border-radius:10px;padding:11px 14px;font-size:13px;cursor:pointer;text-align:center;flex:1}
.btn:hover{border-color:var(--accent)}
.netto{background:linear-gradient(135deg,var(--accent-soft),transparent);border-color:var(--accent)}
.carbox{position:relative;border-radius:14px;overflow:hidden;border:1px dashed var(--accent);background:radial-gradient(ellipse at 50% 115%,var(--accent-soft),transparent 60%),var(--panel);display:flex;align-items:center;justify-content:center;min-height:210px;flex-direction:column;gap:8px}
.carbox .ph{font-size:52px}
.carbox img{max-height:190px;max-width:90%;object-fit:contain}
.mapbox{border-radius:14px;overflow:hidden;border:1px solid var(--line);background:var(--panel2)}
#toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(80px);background:var(--panel);color:var(--txt);border:1px solid var(--accent);border-radius:12px;padding:12px 20px;font-size:14px;opacity:0;transition:.3s;z-index:999}
#toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
`;

const PAGES = {
  p1: `<h1>Panoramica</h1><div class="sub">Batteria, efficienza, ultima ricarica, comandi e storia 7 giorni</div>
  <div class="grid g3">
    <div class="card"><h3>Batteria</h3>
      <div style="display:flex;align-items:flex-end;gap:18px">
        <div class="big" style="color:var(--accent)"><span data-f="batt">—</span><small>%</small></div>
        <div style="margin-left:auto;text-align:right"><div style="font-size:11px;color:var(--muted)">AUTONOMIA</div>
        <div style="font-size:26px;font-weight:800"><span data-f="range">—</span> km</div></div></div>
      <div class="bar"><i data-b="battbar" style="width:0%"></i></div>
      <div class="chips"><span class="chip acc" data-c="loc">📍 —</span><span class="chip" data-c="charging">🔓 Non in carica</span></div>
      <div style="margin-top:14px">
        <div class="row"><span>Odometro</span><b><span data-f="odo">—</span> km</b></div>
        <div class="row"><span>Energia a bordo</span><b><span data-f="batt_kwh">—</span> kWh</b></div>
        <div class="row"><span>Km oggi</span><b><span data-f="km_oggi">—</span> km</b></div>
        <div class="row"><span>Risparmio netto</span><b style="color:var(--good)"><span data-f="risp_tot">—</span> €</b></div></div></div>
    <div class="card"><h3>Efficienza</h3>
      <div class="grid g2" style="gap:10px">
        <div><div class="big" style="font-size:30px" data-f="km_per_kwh">—</div><div style="color:var(--muted);font-size:12px">km/kWh</div></div>
        <div><div class="big" style="font-size:30px" data-f="kwh_100">—</div><div style="color:var(--muted);font-size:12px">kWh/100km</div></div>
        <div><div class="big" style="font-size:30px" data-f="kwh_tot">—</div><div style="color:var(--muted);font-size:12px">kWh consumati</div></div>
        <div><div class="big" style="font-size:30px" data-f="costo_km">—</div><div style="color:var(--muted);font-size:12px">€/km · <span data-f="costo_100">—</span> €/100km</div></div></div>
      <div style="margin-top:12px">
        <div class="row"><span>Viaggio in corso</span><b data-f="trip_attivo">Nessuno</b></div>
        <div class="row"><span>Carica programmata</span><b data-f="t_start">—</b></div></div></div>
    <div class="card"><h3>Ultima ricarica</h3>
      <div class="row"><span>Data</span><b data-f="ultima">—</b></div>
      <div class="row"><span>Energia rete</span><b><span data-f="rete_ult">—</span> kWh</b></div>
      <div class="row"><span>In batteria</span><b><span data-f="batt_ult">—</span> kWh</b></div>
      <div class="row"><span>Efficienza</span><b><span data-f="eff_ric">—</span>%</b></div>
      <div class="row"><span>Perdite</span><b data-f="perdite">—</b></div>
      <div class="row"><span>Costo stimato</span><b><span data-f="costo_corr">—</span> €</b></div></div></div>
  <div class="grid g3" style="margin-top:16px">
    <div class="carbox" data-c="carimg"><div class="ph">🚗</div><b data-f="name">—</b></div>
    <div class="card"><h3>Stato ricarica &amp; comandi</h3>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
        <div class="cmd"><span class="em">🔌</span>Carica<b data-v="cmd_charge">—</b></div>
        <div class="cmd"><span class="em">🔗</span>Presa<b data-v="cmd_plug">—</b></div>
        <div class="cmd"><span class="em">⚡</span>Tipo<b data-v="cmd_tipo">—</b></div>
        <div class="cmd" data-cmd="ac"><span class="em">🧊</span>Avvia A/C<b>Premi ▸</b></div>
        <div class="cmd" data-cmd="charge"><span class="em">🔋</span>Avvia carica<b>Premi ▸</b></div>
        <div class="cmd"><span class="em">⏱</span>Fine stimata<b data-v="cmd_ora">—</b></div></div></div>
    <div class="mapbox">
      <svg viewBox="0 0 400 210" style="display:block;width:100%;height:auto">
        <rect width="400" height="210" fill="var(--panel2)"/>
        <g stroke="var(--line)" stroke-width="5" fill="none">
          <path d="M0 70 L400 50"/><path d="M0 150 L400 170"/><path d="M90 0 L110 210"/><path d="M260 0 L240 210"/></g>
        <path d="M60 180 L140 140 L210 150 L270 100 L340 70" fill="none" stroke="var(--accent)" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="2 7"/>
        <circle cx="340" cy="70" r="8" fill="var(--accent)"/>
        <text x="290" y="55" fill="var(--txt)" font-size="12" font-weight="700">📍 <tspan data-f="loc">—</tspan></text>
        <text x="12" y="24" fill="var(--muted)" font-size="12">Ultima posizione</text></svg></div></div>
  <div class="card" style="margin-top:16px"><h3>Km percorsi (7 giorni)</h3>
    <div style="display:flex;align-items:flex-end;gap:6px;height:120px;max-width:640px" data-c="bars7"></div></div>`,

  p2: `<h1>Viaggi</h1><div class="sub">Albero Anno → Mese → Giorno, da archivio integrazione</div>
  <div class="card tree"><h3>Archivio</h3><div data-c="tree">—</div></div>
  <div class="card" style="margin-top:16px"><h3>Dettaglio viaggi recenti</h3>
    <table><tr><th>Data</th><th>Ora</th><th>Km</th><th>SoC</th><th>kWh</th><th>kWh/100km</th><th>Spesa</th><th>Prima</th></tr>
    <tbody data-c="tab-viaggi"></tbody></table></div>`,

  p3: `<h1>Statistiche</h1><div class="sub">Stile LeapMotor — totali e percorrenza</div>
  <div class="tiles">
    <div class="tile"><div class="em">🏁</div><div><div class="v" style="color:var(--accent)" data-t="tot_viaggi">—</div><div class="l">Totale viaggi</div></div></div>
    <div class="tile"><div class="em">🛣️</div><div><div class="v" data-t="tot_km">—</div><div class="l">Distanza km</div></div></div>
    <div class="tile"><div class="em">📊</div><div><div class="v" data-t="eff_media">—</div><div class="l">Avg efficienza</div></div></div>
    <div class="tile"><div class="em">🏆</div><div><div class="v" style="color:var(--accent)" data-t="eff_best">—</div><div class="l">Best efficienza</div></div></div>
    <div class="tile"><div class="em">⏱️</div><div><div class="v" data-t="tempo">—</div><div class="l">Tempo di guida</div></div></div>
    <div class="tile"><div class="em">🔋</div><div><div class="v" data-t="energia">—</div><div class="l">Energia usata kWh</div></div></div>
    <div class="tile"><div class="em">🔌</div><div><div class="v" data-t="n_ricariche">—</div><div class="l">Ricariche</div></div></div>
    <div class="tile"><div class="em">⚡</div><div><div class="v" data-t="energia_caricata">—</div><div class="l">Energia caricata kWh</div></div></div></div>
  <div class="grid g2">
    <div class="card"><h3>Energia caricata differenziata</h3>
      <div class="row"><span>🏠 Casa (wallbox)</span><b><span data-f="energia_casa">—</span> kWh</b></div>
      <div class="row"><span>☀️ Fotovoltaico</span><b><span data-f="fv_tot">—</span> kWh</b></div>
      <div class="row"><span>⚡ Colonnine fuori casa</span><b data-attr="statistiche_viaggi|energia_colonnine|colonnine">—</b></div></div>
    <div class="card"><h3>Percorrenza</h3>
      <table><tr><th>Periodo</th><th>Usati</th><th>Caricati</th><th>KM</th></tr>
        <tr><td><b>OGGI</b></td><td data-attr="percorrenza|oggi_usati">—</td><td data-attr="percorrenza|oggi_caricati">—</td><td data-attr="percorrenza|oggi_km">—</td></tr>
        <tr><td><b>IERI</b></td><td data-attr="percorrenza|ieri_usati">—</td><td data-attr="percorrenza|ieri_caricati">—</td><td data-attr="percorrenza|ieri_km">—</td></tr>
        <tr><td><b>SETTIMANA</b></td><td data-attr="percorrenza|settimana_usati">—</td><td data-attr="percorrenza|settimana_caricati">—</td><td data-attr="percorrenza|settimana_km">—</td></tr>
        <tr><td><b>MESE</b></td><td data-attr="percorrenza|mese_usati">—</td><td data-attr="percorrenza|mese_caricati">—</td><td data-attr="percorrenza|mese_km">—</td></tr>
        <tr><td><b>ANNO</b></td><td data-attr="percorrenza|anno_usati">—</td><td data-attr="percorrenza|anno_caricati">—</td><td data-attr="percorrenza|anno_km">—</td></tr></table></div></div>`,

  p4: `<h1>Ricariche</h1><div class="sub">Filtri da integrazione + storico</div>
  <div class="tiles">
    <div class="tile" style="flex-direction:column;align-items:flex-start"><div class="l">OGGI</div><div class="v"><span data-f="kwh_oggi_wb">—</span> kWh</div><div style="color:var(--muted);font-size:12px;margin-top:6px"><span data-f="costo_oggi">—</span> €</div></div>
    <div class="tile" style="flex-direction:column;align-items:flex-start"><div class="l">SETTIMANA</div><div class="v"><span data-f="kwh_sett_wb">—</span> kWh</div><div style="color:var(--muted);font-size:12px;margin-top:6px"><span data-f="costo_sett">—</span> €</div></div>
    <div class="tile" style="flex-direction:column;align-items:flex-start"><div class="l">MESE</div><div class="v"><span data-f="kwh_mese_wb">—</span> kWh</div><div style="color:var(--muted);font-size:12px;margin-top:6px"><span data-f="costo_mese">—</span> €</div></div>
    <div class="tile" style="flex-direction:column;align-items:flex-start"><div class="l">ANNO</div><div class="v"><span data-f="kwh_anno_wb">—</span> kWh</div><div style="color:var(--muted);font-size:12px;margin-top:6px"><span data-f="costo_anno">—</span> €</div></div></div>
  <div class="card"><h3>Storico ricariche</h3>
    <table><tr><th>Data</th><th>Tipo</th><th>Durata</th><th>Δ SoC</th><th>kWh</th><th>Ø kW</th><th>€/kWh</th><th>Costo</th></tr>
    <tbody data-c="tab-ricariche"></tbody></table></div>`,

  p5: `<h1>Salute batteria</h1><div class="sub">SOH, efficienza ricarica, perdite</div>
  <div class="grid g3">
    <div class="card"><h3>SOH Ufficiale ✏️</h3>
      <div class="inp" style="border:none"><input data-n="n_soh" style="width:120px;font-size:26px;font-weight:800"><span class="u" style="font-size:16px">%</span></div>
      <div style="color:var(--muted);font-size:12px">modificabile, si salva nel number</div></div>
    <div class="card"><h3>SOH Stimato</h3><div class="big" style="font-size:34px;color:var(--accent)"><span data-f="soh_est">—</span><small>%</small></div>
      <div style="color:var(--muted);font-size:12px;margin-top:8px">dalle ricariche a casa</div></div>
    <div class="card"><h3>kWh per 1%</h3><div class="big" style="font-size:34px;color:var(--accent)"><span data-f="kwh_1pct">—</span> <small>kWh</small></div>
      <div style="color:var(--muted);font-size:12px;margin-top:8px">= capacità × SOH ÷ 100</div></div></div>
  <div class="grid g2" style="margin-top:16px">
    <div class="card"><h3>Ultima sessione</h3>
      <div class="row"><span>Dalla rete (AC)</span><b><span data-f="rete_ult">—</span> kWh</b></div>
      <div class="row"><span>In batteria</span><b><span data-f="batt_ult">—</span> kWh</b></div>
      <div class="row"><span>Efficienza</span><b><span data-f="eff_ric">—</span>%</b></div></div>
    <div class="card"><h3>Sessioni analizzate</h3>
      <table><tr><th>Data</th><th>Δ SoC</th><th>Rete</th><th>Batteria</th><th>Eff.</th></tr>
      <tbody data-c="tab-salute"></tbody></table></div></div>`,

  p6: `<h1>Manutenzione</h1><div class="sub">Tagliandi e Assicurazione</div>
  <div class="grid g2">
    <div class="card"><h3>🔧 Tagliandi</h3>
      <div class="row"><span>Prossimo</span><b data-attr="tagliandi|prossimo|next">—</b></div>
      <div class="row"><span>Modalità</span><b data-attr="tagliandi|modalita|mode">—</b></div>
      <div class="row"><span>Speso finora</span><b data-attr="tagliandi|speso|totale">—</b></div>
      <div class="row"><span>Interventi</span><b data-attr="tagliandi|interventi|n">—</b></div></div>
    <div class="card"><h3>🛡️ Assicurazione</h3>
      <div class="row"><span>Scadenza</span><b data-attr="assicurazione|scadenza|data">—</b></div>
      <div class="row"><span>Giorni rimasti</span><b data-attr="assicurazione|giorni|gg_rimasti">—</b></div>
      <div class="inp"><span>Costo annuo</span><input data-n="n_assic"><span class="u">€/anno</span></div>
      <div style="display:flex;gap:8px;margin-top:14px">
        <div class="btn" data-cmd="ass_plus6">Rinnova +6 mesi</div>
        <div class="btn" data-cmd="ass_plus12">Rinnova +1 anno</div></div></div></div>
  <div class="card netto" style="margin-top:16px"><h3>🏆 Risparmio manutenzione</h3>
    <div class="row"><span>Risparmio tagliandi vs termica</span><b><span data-f="risp_tagliandi">—</span> €</b></div>
    <div class="row"><span>Risparmio bollo</span><b><span data-f="risp_bollo">—</span> €</b></div></div>`,

  p7: `<h1>Risparmi</h1><div class="sub">Il quadro completo</div>
  <div class="grid g2">
    <div class="card"><h3>💶 Carburante</h3>
      <div class="row"><span>Risparmiato TOTALE</span><b style="color:var(--accent)"><span data-f="risp_tot">—</span> €</b></div>
      <div class="row"><span>Spesa teorica termica</span><b><span data-f="spesa_teorica">—</span> €</b></div>
      <div class="row"><span>Costo totale ricariche</span><b><span data-f="costo_ric_tot">—</span> €</b></div>
      <div class="row"><span>Risparmiato MESE</span><b><span data-f="risp_mese">—</span> €</b></div>
      <div class="row"><span>Risparmiato ANNO</span><b><span data-f="risp_anno">—</span> €</b></div></div>
    <div class="card"><h3>🔧📄 Manutenzione + Bollo</h3>
      <div class="row"><span>Risparmio tagliandi</span><b><span data-f="risp_tagliandi">—</span> €</b></div>
      <div class="row"><span>Risparmio bollo</span><b><span data-f="risp_bollo">—</span> €</b></div></div></div>
  <div class="card netto" style="margin-top:16px"><h3>🏆 Risultato netto</h3>
    <table><tr><th>Voce</th><th>Euro</th></tr>
      <tr><td>Carburante evitato</td><td><span data-f="risp_tot">—</span> €</td></tr>
      <tr><td>+ Tagliandi</td><td><span data-f="risp_tagliandi">—</span> €</td></tr>
      <tr><td>+ Bollo</td><td><span data-f="risp_bollo">—</span> €</td></tr></table></div>
  <div class="grid g2" style="margin-top:16px">
    <div class="card"><h3>☀️ Fotovoltaico</h3>
      <div class="row"><span>Ricaricato FV questo mese</span><b><span data-f="fv_mese">—</span> kWh</b></div>
      <div class="row"><span>Energia FV totale</span><b><span data-f="fv_tot">—</span> kWh</b></div></div>
    <div class="card"><h3>ℹ️ Come si calcola</h3>
      <div style="color:var(--muted);font-size:12.5px;line-height:1.7">Carburante: km × consumo × prezzo − costi pagati.<br>Tagliandi: (km ÷ intervallo) × 450 € − spesa reale EV.<br>Bollo: anni × differenza. Il FV costa 0 €.</div></div></div>`,

  p8: `<h1>Extra</h1><div class="sub">Vampire drain, CO2, scadenze, rotte, top &amp; stop</div>
  <div class="grid g3">
    <div class="card"><h3>🔋 Vampire drain oggi</h3><div class="big" style="font-size:32px;color:var(--accent)"><span data-f="drain">—</span><small>%</small></div></div>
    <div class="card"><h3>🌍 CO2</h3><div class="big" style="font-size:32px;color:var(--good)" data-f="co2">—</div></div>
    <div class="card"><h3>📅 Scadenze</h3><div class="row"><span>Prossima</span><b data-attr="scadenze|prossima|tipo">—</b></div>
      <div class="row"><span>Giorni</span><b data-attr="scadenze|giorni|gg">—</b></div></div></div>
  <div class="grid g2" style="margin-top:16px">
    <div class="card"><h3>Consumo per zona</h3>
      <table><tr><th>Rotta</th><th>Viaggi</th><th>Km</th><th>kWh/100km</th></tr><tbody data-attr-list="consumo_per_zona"></tbody></table></div>
    <div class="card"><h3>🏆 Top &amp; Stop · mese</h3>
      <div class="row"><span>Migliore / Peggiore</span><b data-f="topstop">—</b></div>
      <div class="row"><span>Energia casa (totale)</span><b><span data-f="energia_casa">—</span> kWh</b></div></div></div>`,

  p9: `<h1>Automazioni</h1><div class="sub">Notifiche e carica programmata integrate — attivabili da qui</div>
  <div class="grid g2">
    <div class="card"><h3>Notifiche</h3>
      <div class="row"><span>⚡ Avvio ricarica</span><label class="switch"><input type="checkbox" data-sw="sw_start"><span></span></label></div>
      <div class="row"><span>🔋 Fine ricarica (kWh, SoC, costo)</span><label class="switch"><input type="checkbox" data-sw="sw_end"><span></span></label></div>
      <div class="row"><span>⚠️ Batteria bassa a casa</span><label class="switch"><input type="checkbox" data-sw="sw_low"><span></span></label></div>
      <div class="row"><span>📨 Servizio notify</span><b data-f="notify">—</b></div></div>
    <div class="card"><h3>⏰ Carica programmata</h3>
      <div class="row"><span>Stato</span><label class="switch"><input type="checkbox" data-sw="sw_sched"><span></span></label></div>
      <div class="row"><span>↳ Orario avvio</span><b data-f="t_start">—</b></div>
      <div class="row"><span>↳ Orario stop</span><b data-f="t_stop">—</b></div>
      <div class="row"><span>↳ Fascia promemoria</span><b><span data-f="t_low_start">—</span> → <span data-f="t_low_end">—</span></b></div></div></div>
  <div class="card" style="margin-top:16px"><h3>Come si cambiano i parametri</h3>
    <div style="color:var(--muted);font-size:13px;line-height:1.8">
      Tutto in <b>Impostazioni → Integrazioni → Renault EV Center → Configura</b>:
      servizio notify, % minima e fascia oraria del promemoria, modalità programmazione
      (orario o %), orari e % di avvio/stop, pulsante di avvio carica e number target
      per lo stop. Gli interruttori si trovano anche tra i dispositivi
      ("Renault EV Center" → switch).</div></div>`,

  p10: `<h1>Impostazioni</h1><div class="sub">Prezzi, batteria, notifiche, palette e reset — salvati nell'integrazione</div>
  <div class="grid g3">
    <div class="card"><h3>Prezzi energia</h3>
      <div class="inp"><span>Costo casa</span><input data-n="n_price_home"><span class="u">€/kWh</span></div>
      <div class="inp"><span>Costo colonnina</span><input data-n="n_price_public"><span class="u">€/kWh</span></div>
      <div class="inp"><span>Costo fotovoltaico</span><input data-n="n_price_solar"><span class="u">€/kWh</span></div>
      <div class="inp"><span>Prezzo diesel (o sensore live)</span><input data-ls="rec_diesel" data-f="diesel" value="1.72"><span class="u">€/l</span></div></div>
    <div class="card"><h3>Batteria</h3>
      <div class="inp"><span>Obiettivo ricarica</span><input data-n="n_target"><span class="u">%</span></div>
      <div class="inp"><span>Capacità</span><input data-n="n_capacity"><span class="u">kWh</span></div>
      <div class="inp"><span>SOH ufficiale</span><input data-n="n_soh"><span class="u">%</span></div>
      <div class="inp"><span>Costo assicurazione</span><input data-n="n_assic"><span class="u">€/anno</span></div>
      <div class="inp"><span>🏠 Priorità batteria casa</span><input data-n="n_prio"><span class="u">%</span></div></div>
    <div class="card"><h3>Reset &amp; export</h3>
      <div style="display:flex;flex-direction:column;gap:8px">
        <div class="btn" data-cmd="close_trip">🏁 Chiudi viaggio ora</div>
        <div class="btn" data-cmd="reset_km">🔄 Reset contatori Km</div>
        <div class="btn" data-cmd="reset_energia">🔄 Reset contatori Energia</div>
        <div class="btn" data-cmd="reset_costi">🔄 Reset contatori Costi</div>
        <div class="btn" data-cmd="csv">📥 Esporta viaggi CSV</div></div></div></div>
  <div class="card" style="margin-top:16px"><h3>🔔 Notifiche</h3>
    <div class="inp"><span>Servizio notify (es. notify.michele)</span><input data-ls="rec_notify" data-f="notify" style="width:170px"><span class="u"></span></div>
    <div class="inp"><span>Giorni preavviso scadenze</span><input data-ls="rec_preavviso" value="30"><span class="u">gg</span></div></div>
  <div class="card" style="margin-top:16px"><h3>🤖 Automazioni</h3>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <div class="btn" data-cmd="create_automations">✨ Crea automazioni consigliate</div></div>
    <div class="note">Crea in Home Assistant 3 automazioni pronte: <b>ricarica completata</b> (kWh, SoC, costo),
      <b>batteria bassa fuori casa</b>, <b>riassunto giornaliero</b> alle 21:30. Sono modificabili da
      Impostazioni → Automazioni. Notifiche via persistent_notification se nessun servizio notify configurato.</div></div>`,
};

customElements.define("renault-ev-center-panel", RenaultEvCenterPanel);


