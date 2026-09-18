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

/** Versione compilata: usata per l'auto-refresh quando l'integrazione viene aggiornata. */
const REC_VER = "1.0.12";
let _recVerChecked = false;

class RenaultEvCenterPanel extends HTMLElement {
  /** Se la versione servita (config della card) differisce dalla mia, ricarica la pagina una volta. */
  _checkVersion(serverVer) {
    if (_recVerChecked) return;
    _recVerChecked = true;
    console.info(`Renault EV Center: JS ${REC_VER} · integrazione ${serverVer || "non dichiarata"}`);
    // 1) la config della card dichiara la versione dell'integrazione (fonte affidabile)
    if (serverVer) {
      if (serverVer !== REC_VER) this._reloadOnce(serverVer);
      return;
    }
    // 2) niente version in config (dashboard creata da versioni vecchie): lascia lavorare
    //    _startVersionWatch(), che legge l'attributo del sensore via websocket.
  }
  /**
   * Auto-refresh: la versione arriva via **websocket** nell'attributo `version` del sensore
   * <name>_prossima_scadenza. Affidabile: nessuna cache HTTP/Service Worker di mezzo.
   * Il fetch resta come ripiego per integrazioni vecchie (senza l'attributo).
   */
  _startVersionWatch() {
    if (this._verTimer) return;
    const entity = this._sid("prossima_scadenza");
    const check = () => {
      try {
        const st = this._hass && this._hass.states && this._hass.states[entity];
        const v = st && st.attributes ? st.attributes.version : null;
        if (v) {                       // websocket: dato sempre fresco
          if (v !== REC_VER) this._reloadOnce(v);
          return;
        }
      } catch (e) { /* ignore */ }
      // ripiego: rilegge il file servito
      fetch(`/local/renault-ev-center/renault-ev-center-panel.js?ts=${Date.now()}`, { cache: "no-store" })
        .then((r) => (r.ok ? r.text() : ""))
        .then((t) => {
          const m = t && t.match(/const REC_VER = "([^"]+)"/);
          if (m && m[1] !== REC_VER) this._reloadOnce(m[1]);
        })
        .catch(() => {});
    };
    this._verTimer = setInterval(check, 60000); // 1 minuto
    setTimeout(check, 3000);
  }
  _reloadOnce(ver) {
    try {
      const key = "rec_ver_" + ver;
      if (sessionStorage.getItem(key)) return;
      sessionStorage.setItem(key, "1");
    } catch (e) { /* storage negato: meglio ricaricare una volta in più che restare vecchi */ }
    console.info(`Renault EV Center: aggiorno da ${REC_VER} a ${ver}`);
    // cache-bust: cambia l'URL, così il browser non ripesca la pagina dalla cache
    try {
      const u = new URL(location.href);
      u.searchParams.set("_recv", ver);
      location.replace(u.toString());
      return;
    } catch (e) { /* URL non manipolabile: fallback */ }
    location.reload();
  }
  setConfig(config) {
    if (!config) config = {};
    this._checkVersion(config.version);
    this._startVersionWatch();
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
    try {
      if (!this._built) this._build();
      else if (!this._raf) this._raf = requestAnimationFrame(() => {
        this._raf = null;
        try { if (!PAGES[this._page]) this._page = "p1"; this._update(); }
        catch (e) { this._showError(e); }
      });
    } catch (e) { this._showError(e); }
  }

  _showError(e) {
    try {
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });
      const msg = (e && e.stack) ? e.stack : String(e);
      this.shadowRoot.innerHTML = `<div style="padding:16px;background:#1a0f12;color:#f87171;font-family:monospace;font-size:12px;white-space:pre-wrap">Renault EV Center — errore:<br>${msg}</div>`;
    } catch (e2) { /* noop */ }
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
    const v = s ? this._attrAny(s, ["list", "items", "trips", "days", "viaggi", "ricariche", "data", "rows", "righe", "rotte"]) : null;
    return Array.isArray(v) ? v : [];
  }
  _fmt(v, dec = 1) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return v.toLocaleString("it-IT", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }
  _i(v) { return v === null || v === undefined || isNaN(v) ? "—" : Math.round(v).toLocaleString("it-IT"); }
  _d(iso) { const m = String(iso || "").match(/^(\d{4})-(\d{2})-(\d{2})/); return m ? `${m[3]}-${m[2]}-${m[1]}` : (iso || "—"); }
  _zn(z) {
    const s = String(z ?? "").trim();
    if (!s || s === "—" || s === "null" || s === "undefined") return "—";
    if (s === "home") return "Casa";
    if (s === "not_home") return "Fuori";
    return s.replace(/_/g, " ").replace(/^\w/, (m) => m.toUpperCase());
  }

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
      case "batt": return S._ov("battery") ? S._num(S._ov("battery")) : S._num(S._car("sensor", "battery"), S._car("sensor", "battery_level"), S._sid("batteria"));
      case "range": return S._ov("range") ? S._num(S._ov("range")) : S._num(S._car("sensor", "range_electric"), S._car("sensor", "battery_autonomy"), S._sid("autonomia_della_batteria"));
      case "odo": return S._ov("odometer") ? S._num(S._ov("odometer")) : S._num(S._car("sensor", "odometer"), S._sid("chilometraggio"));
      case "loc": {
        const s = S._ov("location") ? S._hass.states[S._ov("location")] : (S._hass.states[S._car("device_tracker", "location")] || S._hass.states[S._sid("posizione")]);
        return s ? (s.attributes.friendly_name || s.state) : null;
      }
      case "charging": return S._ov("charging") ? S._hass.states[S._ov("charging")] : S._st(S._bid("in_carica"), S._sid("stato_di_carica"), S._sid("stato_ricarica_attuale"), S._car("sensor", "battery_state"), S._car("sensor", "charging_mode"), `binary_sensor.wallbox_${c}`);
      case "plug": return S._st(S._car("binary_sensor", "plug_status"), S._car("binary_sensor", "plugged_in"), S._sid("stato_della_spina"), `binary_sensor.wallbox_${c}`);
      case "batt_kwh": return S._num(S._sid("batteria_kwh_disponibili"), "sensor.megane_battery_available_energy_2", S._car("sensor", "battery_remaining_capacity"));
      case "km_oggi": {
        const rows = S._list(S._sid("percorrenza"));
        const r = rows.find((x) => S._slug(String(x.nome ?? "")) === "oggi");
        const v = r ? (parseFloat(r.km) || 0) : null;
        if (v !== null && v > 0) return v;
        return S._num("sensor.km_giornalieri", S._sid("km_giornalieri"), S._sid("km_oggi_trip"));
      }
      case "kwh_oggi_k": {
        const rows = S._list(S._sid("percorrenza"));
        const r = rows.find((x) => S._slug(String(x.nome ?? "")) === "oggi");
        const v = r ? (parseFloat(r.usati) || 0) : null;
        if (v !== null && v > 0) return v;
        const m = S._num(S._sid("battery_energy_daily_discharge"), "sensor.megane_battery_energy_daily_discharge", S._sid("kwh_usati_giorno"), S._sid("kwh_oggi"));
        if (m !== null && Math.abs(m) > 0.05) return Math.abs(m);
        const pct = r ? (parseFloat(r.pct) || 0) : 0;
        if (pct > 0) return Math.round(pct / 100 * (parseFloat(S._cfg.capacity) || 60) * 100) / 100;
        return m === null ? null : Math.abs(m);
      }
      case "km_per_kwh": {
        const k = S._num(S._sid("km_per_kwh"), "sensor.megane_km_per_kwh");
        if (k !== null && k > 0) return k;
        const e = S._field("kwh_100");
        return (typeof e === "number" && e > 0) ? 100 / e : null;
      }
      case "kwh_100": {
        const e = S._num(S._sid("kwh_per_100km"), S._sid("kwh_per_100_km"), "sensor.megane_kwh_per_100_km");
        if (e !== null && e > 0) return e;
        const b = S._num("sensor.megane_batteria_per_100_km");
        return (b === null || b <= 0) ? e : b * (parseFloat(S._cfg.capacity) || 60) / 100;
      }
      case "kwh_tot": return S._num(S._sid("kwh_totali_consumati"), "sensor.megane_kwh_totali");
      case "stat_km_tot": { const s = S._st(S._sid("statistiche_viaggi")); return s ? S._attrAny(s, ["km_totali"]) : null; }
      case "stat_n_trip": { const s = S._st(S._sid("statistiche_viaggi")); return s ? S._attrAny(s, ["totale_viaggi", "n_trip"]) : null; }
      case "stat_eff": { const s = S._st(S._sid("statistiche_viaggi")); return s ? S._attrAny(s, ["efficienza_media", "kwh_per_100km"]) : null; }
      case "costo_km": return S._num(S._sid("costo_per_km"), "sensor.costo_per_km_megane");
      case "costo_100": {
        const c100 = S._num(S._sid("costo_per_100_km"), "sensor.costo_per_100_km_megane");
        if (c100 !== null && c100 > 0) return c100;
        const k = S._field("costo_km");
        return (typeof k === "number" && k > 0) ? k * 100 : c100;
      }
      case "risp_netto_tot": {
        const vs = [S._field("risp_tot"), S._field("risp_tagliandi"), S._field("risp_bollo")].filter((v) => typeof v === "number");
        return vs.length ? vs.reduce((a, v) => a + v, 0) : null;
      }
      case "ricarica_oggi_pct": return S._num(S._sid("battery_perc_giorno_charge"), "sensor.megane_battery_perc_giorno_charge");
      case "risp_tot": {
        const rv = S._num(S._sid("risparmio_totale_vs_diesel"));
        if (rv !== null) return rv;
        const t = S._spesaTeo(S._field("odo"));
        const c = S._num(S._sid("costo_ricarica_totale"));
        return (t === null || c === null) ? null : t - c;
      }
      case "trip_attivo": {
        const s = S._st(S._sid("trip_attivo"));
        if (!s) return null;
        return s.state === "on" ? "🚗 Auto in movimento" : "🅿️ Auto parcheggiata";
      }
      // Ultima ricarica / ricariche
      case "media_ult": {
        const r = S._list(S._sid("lista_ricariche"))[0];
        const v = r ? (r.potenza_media_kw ?? r.media_kw ?? r.potenza_media ?? r.power ?? null) : null;
        const n = S._num(S._sid("potenza_media_ultima_ricarica"), S._sid("media_kW"), S._sid("potenza_media_kw"));
        const wp = S._field("wb_potenza");
        return v ?? n ?? (typeof wp === "number" && wp > 0 ? wp : null);
      }
      case "ultima": return S._st(S._sid("ultima_ricarica"));
      case "ultima_data": {
        const rs = S._list(S._sid("lista_ricariche"));
        const r = rs[0];
        if (r) return `${this._d(r.data ?? r.giorno)}${r.ora_inizio ? " · " + r.ora_inizio : ""}`;
        const s = S._st(S._sid("ultima_data_ricarica"), "sensor.ultima_data_ricarica_megane", "sensor.ultima_ricarica");
        return s ? S._txt(s) : null;
      }
      case "batt_ult_pct": {
        const r = S._list(S._sid("lista_ricariche"))[0];
        const a = r ? (r.soc_start ?? r.soc_inizio ?? r.inizio ?? r.start ?? null) : null;
        const b = r ? (r.soc_end ?? r.soc_fine ?? r.fine ?? r.end ?? null) : null;
        if (a !== null && b !== null) return `${Math.round(a)}% → ${Math.round(b)}%`;
        const start = S._num(S._sid("soc_inizio_carica"), "sensor.megane_soc_inizio_carica");
        const delta = S._num(S._sid("ultima_ricarica_delta_batteria"), "sensor.ultima_ricarica_delta_batteria");
        return (start === null || delta === null) ? null : `${Math.round(start)}% → ${Math.round(Math.min(100, start + Math.abs(delta)))}%`;
      }
      case "kwh_oggi_wb": return S._num("sensor.megane_battery_energy_daily_charge", S._sid("battery_energy_daily_charge"), S._sid("energia_caricata_giornaliera"), S._sid("wb_energy_oggi"), S._sid("ricariche_oggi"));
      case "kwh_sett_wb": return S._num(S._sid("energia_caricata_settimanale"), S._sid("wb_energy_settimana"), S._sid("ricariche_settimana"), "sensor.megane_battery_energy_weekly_charge");
      case "kwh_mese_wb": return S._num(S._sid("energia_caricata_mensile"), S._sid("wb_energy_mese"), S._sid("ricariche_mese"), "sensor.megane_battery_energy_monthly_charge");
      case "kwh_anno_wb": return S._num(S._sid("energia_caricata_annuale"), S._sid("wb_energy_anno"), S._sid("ricariche_anno"), "sensor.megane_battery_energy_yearly_charge");
      case "costo_oggi": return S._num(S._sid("costo_ricarica_giornaliero"), S._sid("costo_ricarica_oggi"), "sensor.costo_ricarica_oggi");
      case "costo_sett": return S._num(S._sid("costo_ricarica_settimanale"), S._sid("costo_ricarica_settimana"), "sensor.costo_ricarica_settimana");
      case "costo_mese": return S._num(S._sid("costo_ricarica_mensile"), S._sid("costo_ricarica_mese"), "sensor.costo_ricarica_mese");
      case "costo_anno": return S._num(S._sid("costo_ricarica_annuale"), S._sid("costo_ricarica_anno"), "sensor.costo_ricarica_anno");
      case "lista_ric": return S._list(S._sid("lista_ricariche"));
      case "wb_potenza": return S._num(S._sid("wallbox_potenza"));
      case "tipo_ric": return S._st(S._sid("tipo_ricarica_attuale"), "sensor.megane_charger_type", "sensor.megane_charging_mode");
      case "tempo_ric": return S._st(S._sid("tempo_ricarica_stimato"), S._car("sensor", "remaining_charge_time"));
      case "ora_compl": return S._st(S._sid("ora_completamento_ricarica"), "sensor.ora_completamento_ricarica", S._car("sensor", "remaining_charge_time"));
      case "costo_corr": return S._num(S._sid("costo_ricarica_corrente_stimato"), "sensor.costo_ricarica_corrente_stimato");
      // Statistiche
      case "stats": return S._st(S._sid("statistiche_viaggi"));
      case "percorrenza": return S._st(S._sid("percorrenza"));
      case "storico": return S._list(S._sid("storico_giornaliero"));
      case "energia_casa": return S._num(S._sid("energia_caricata_casa_totale"), "sensor.megane_battery_energy_total_charge");
      case "fv_tot": return S._num(S._sid("energia_caricata_fotovoltaico_totale"), "sensor.energia_caricata_fotovoltaico_totale");
      case "fv_mese": return S._num(S._sid("ricaricato_fotovoltaico_mese"), "sensor.energia_caricata_fotovoltaico_mensile");
      // Salute
      case "cap_nom": {
        const n = S._field("n_capacity");
        const st = typeof n === "string" ? S._hass.states[n] : null;
        const v = st ? parseFloat(st.state) : NaN;
        return isNaN(v) ? (parseFloat(S._cfg.capacity) || 60) : v;
      }
      case "cap_stim": {
        const nom = S._field("cap_nom");
        const soh = S._num(S._sid("soh_stimato"), "sensor.megane_soh_stimato");
        return (typeof nom === "number" && soh !== null && soh > 0) ? Math.round(nom * soh / 100 * 10) / 10 : null;
      }
      case "soh_off": return S._num(S._nid("soh_ufficiale"), "sensor.megane_soh_ufficiale");
      case "soh_est": return S._num(S._sid("soh_stimato"), "sensor.megane_soh_stimato");
      case "kwh_1pct": return S._num(S._sid("kwh_per_1_batteria"), S._sid("kwh_per_1pct"), "sensor.megane_kwh_per_1");
      case "eff_ric": return S._num(S._sid("efficienza_ricarica"), "sensor.megane_efficienza");
      case "perdite": return S._st(S._sid("perdite_ultima_ricarica"));
      case "batt_ult": return S._num(S._sid("energia_batteria_ultima_ricarica"), S._sid("energia_teorica_sessione"), "sensor.megane_energia_teorica_sessione");
      case "rete_ult": { const s = S._st(S._sid("energia_batteria_ultima_ricarica")); const v = s ? S._attrAny(s, ["dalla_rete_kwh"]) : null; return v === null ? S._num(S._sid("ultima_ricarica")) : parseFloat(v); }
      case "dispersa_ult": { const s = S._st(S._sid("energia_batteria_ultima_ricarica")); const v = s ? S._attrAny(s, ["dispersa_kwh"]) : null; return v === null ? null : parseFloat(v); }
      // Manutenzione
      case "tagliandi": return S._st(S._sid("tagliandi"));
      case "assic": return S._st(S._sid("assicurazione"));
      case "scadenze": return S._st(S._sid("prossima_scadenza"));
      case "teo_tagliandi": { const km = S._num(S._sid("chilometraggio"), S._ov("odometer"), S._car("sensor", "odometer")); const st = S._st(S._sid("tagliandi")); const iv = st ? (S._attrAny(st, ["intervallo_km"]) || 15000) : 15000; return km === null ? null : Math.floor(km / iv) * 450; }
      case "risp_tagliandi": { const v0 = S._num(S._sid("risparmio_tagliandi_vs_diesel")); if (v0 !== null) return v0; const km = S._num(S._sid("chilometraggio"), S._ov("odometer"), S._car("sensor", "odometer")); const iv = S._num(S._sid("tagliandi")) === null ? null : (S._attrAny(S._st(S._sid("tagliandi")), ["intervallo_km"]) || 15000); const sp = S._num(S._sid("tagliandi")); return (km === null || iv === null || sp === null || iv <= 0) ? null : Math.floor(km / iv) * 450 - sp; }
      case "risp_bollo": { const v = S._num(S._sid("risparmio_bollo_vs_diesel")); return v !== null ? v : (S._ov("bollo_termico") ? S._num(S._ov("bollo_termico")) : null); }
      case "assic_costo": return S._num(S._nid("assic_costo"), S._nid("costo_assicurazione"));
      // Risparmi carburante: entità risparmio_* dell'integrazione, altrimenti calcolo client
      case "risp_mese": { const v = S._num(S._sid("risparmio_mese_vs_diesel")); return v !== null ? v : S._rispKm(S._num(S._sid("km_mensili")), S._num(S._sid("costo_ricarica_mensile"), S._sid("costo_ricarica_mese"))); }
      case "risp_anno": { const v = S._num(S._sid("risparmio_anno_vs_diesel")); return v !== null ? v : S._rispKm(S._num(S._sid("km_annuali")), S._num(S._sid("costo_ricarica_annuale"), S._sid("costo_ricarica_anno"))); }
      case "spesa_teorica": {
        if (S._ov("spesa_teorica")) return S._num(S._ov("spesa_teorica"));
        const st = S._st(S._sid("risparmio_totale_vs_diesel"));
        const tt = st ? S._attrAny(st, ["termica_totale"]) : null;
        if (tt !== null) return tt;
        return S._spesaTeo(S._field("odo"));
      }
      case "costo_ric_tot": { const v = S._num(S._sid("costo_ricarica_totale")); if (v) return v; const st = S._st(S._sid("risparmio_totale_vs_diesel")); const e = st ? S._attrAny(st, ["elettrico_totale"]) : null; if (e !== null && e !== undefined && e !== 0) return e; return v === 0 ? 0 : (S._ov("costo_ric_tot") ? S._num(S._ov("costo_ric_tot")) : null); }
      // Extra
      case "drain": {
        // sensore integrazione = max(scarica totale giornaliera, somma viaggi) → include anche il fermo
        const v = S._num(S._sid("batteria_scaricata_oggi"), S._sid("battery_perc_giorno_discharge"), "sensor.megane_battery_perc_giorno_discharge");
        if (v !== null && Math.abs(v) > 0) return Math.round(Math.abs(v) * 10) / 10;
        const rows = S._list(S._sid("percorrenza"));
        const r = rows.find((x) => S._slug(String(x.nome ?? "")) === "oggi");
        const p = r ? (parseFloat(r.pct) || 0) : 0;
        if (p > 0) return Math.round(p * 10) / 10;
        const kwh = S._field("kwh_oggi_k");
        const cap = parseFloat(S._cfg.capacity) || 60;
        if (typeof kwh === "number" && kwh > 0) return Math.round(kwh / cap * 1000) / 10;
        return null;
      }
      case "perc_100km": {
        const v = S._num(S._sid("batteria_per_100km"), "sensor.megane_batteria_per_100_km");
        if (v !== null && v > 0) return v;
        // ripiego: % consumata oggi sui km di oggi (dati reali della batteria)
        const km = S._field("km_oggi");
        const d = S._field("drain");
        return (typeof km === "number" && km > 0.5 && typeof d === "number") ? d / km * 100 : v;
      }
      case "vampire": return S._num(S._sid("batteria_persa_da_fermo_oggi"));
      case "drain_mese_pct": return S._num(S._sid("batteria_persa_da_fermo_mese"));
      case "temp_est": {
        const v = S._num(S._sid("temperatura_esterna"), S._sid("temp_esterna"));
        if (v !== null) return v;
        // fallback: temperatura attuale del meteo HA (weather.*)
        for (const id in S._hass.states) {
          if (!id.startsWith("weather.")) continue;
          const t = S._hass.states[id] && S._hass.states[id].attributes && S._hass.states[id].attributes.temperature;
          if (t !== null && t !== undefined && !isNaN(t)) return t;
        }
        return null;
      }
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
      case "n_low_soc": return S._nid("batteria_minima_promemoria");
      case "sw_start": return S._swid("notifica_avvio_ricarica");
      case "sw_end": return S._swid("notifica_fine_ricarica");
      case "sw_low": return S._swid("promemoria_batteria_bassa");
      case "sw_sched": return S._swid("carica_programmata");
      case "sw_bal": return S._swid("bilanciamento_solare");
      case "t_start": return S._tid("carica_orario_avvio");
      case "t_start_v": { const s = S._st(S._tid("carica_orario_avvio")); return s && typeof s.state === "string" ? s.state.slice(0, 5) : null; }
      case "t_stop": return S._tid("carica_orario_stop");
      case "t_low_start": return S._tid("promemoria_inizio");
      case "t_low_end": return S._tid("promemoria_fine");
      case "sel_tipo": return S._selid("filtro_tipo_ricarica");
      case "sel_periodo": return S._selid("filtro_periodo_ricariche");
      case "sel_anno": return S._selid("filtro_anno_ricariche");
      default: return null;
    }
  }
  _txt(v) {
    if (v === null || v === undefined) return "—";
    if (typeof v === "object") {
      const s = v.state;
      return s === undefined || s === null || s === "unavailable" || s === "unknown" ? "—" : String(s);
    }
    return String(v);
  }
  _f(k) { return this._txt(this._field(k)); }
  /** primo entity_id live per un campo KPI cliccabile */
  _ent(k) {
    const S = this;
    const cands = {
      charging: [S._car("binary_sensor", "in_carica"), S._sid("in_carica")],
      plug: [S._car("binary_sensor", "spina"), S._sid("stato_della_spina")],
      loc: [S._car("device_tracker", "posizione"), S._sid("posizione")],
      ora_compl: [S._sid("ora_completamento_ricarica"), S._car("sensor", "remaining_charge_time")],
      batt: [S._ov("battery"), S._car("sensor", "batteria"), S._car("sensor", "battery_level"), S._sid("batteria")],
      range: [S._ov("range"), S._car("sensor", "range_electric"), S._sid("autonomia_della_batteria")],
      odo: [S._ov("odometer"), S._car("sensor", "odometer"), S._sid("chilometraggio")],
      batt_kwh: [S._sid("batteria_kwh_disponibili"), "sensor.megane_battery_available_energy_2"],
      km_oggi: [S._sid("km_giornalieri"), "sensor.km_giornalieri"],
      kwh_oggi_k: [S._sid("battery_energy_daily_discharge"), "sensor.megane_battery_energy_daily_discharge", S._sid("energia_batteria_giornaliero"), S._sid("batteria_scaricata_oggi")],
      drain: [S._sid("battery_perc_giorno_discharge"), "sensor.megane_battery_perc_giorno_discharge", S._sid("batteria_scaricata_oggi")],
      km_per_kwh: [S._sid("km_per_kwh"), "sensor.megane_km_per_kwh"],
      kwh_100: [S._sid("kwh_per_100km"), "sensor.megane_kwh_per_100_km"],
      perc_100km: [S._sid("batteria_per_100km"), "sensor.megane_batteria_per_100_km"],
      costo_km: [S._sid("costo_per_km"), "sensor.costo_per_km_megane"],
      costo_100: [S._sid("costo_per_100_km"), "sensor.costo_per_100_km_megane"],
      kwh_tot: [S._sid("kwh_totali_consumati"), "sensor.megane_kwh_totali"],
      wb_potenza: [S._sid("wallbox_potenza"), "sensor.wallbox_instant_power", S._car("sensor", "battery_charger_power")],
      temp_est: [S._sid("temperatura_esterna"), S._sid("temp_esterna")],
      media_ult: [S._sid("potenza_media_ultima_ricarica")],
      eff_ric: [S._sid("efficienza_ricarica"), "sensor.megane_efficienza"],
    };
    for (const id of (cands[k] || [])) {
      if (id && this._hass.states[id]) return id;
    }
    return null;
  }
  _moreInfo(entityId) {
    const ev = new Event("hass-more-info", { bubbles: true, composed: true });
    ev.detail = { entityId };
    this.dispatchEvent(ev);
  }
  _on(k) { const s = this._field(k); return s && s.state === "on"; }
  /** plug: binary_sensor on|off oppure sensor testuale (plugged/unplugged, collegata/scollegata) */
  _plugOn() {
    const s = this._field("plug");
    if (!s) return false;
    const v = this._slug(s.state);
    return s.state === "on" || (/(plug|connect|collegat|conness|inserit)/.test(v) && !/(unplug|disconn|scollegat|non_)/.test(v));
  }
  /** carica: binary_sensor on|off oppure sensor testuale (charging/not_charging, in_carica/non_in_carica) */
  _chargeOn() {
    const s = this._field("charging");
    if (!s) return false;
    const v = this._slug(s.state);
    return s.state === "on" || (/(charg|carica)/.test(v) && !/(not|no_|non_|end|finit|terminat|stop)/.test(v));
  }
  /** zona dell'auto: tracker configurato o dell'integrazione (in_zones o state) */
  _zoneName() {
    for (const id of [
      this._ov("location"),
      `device_tracker.${this._slug(this._cfg.name)}_posizione`,
      this._car("device_tracker", "location"),
      this._car("device_tracker", ""),
    ]) {
      const s = id ? this._hass.states[id] : null;
      if (!s || s.state === "unavailable" || s.state === "unknown") continue;
      const z = Array.isArray(s.attributes.in_zones) ? s.attributes.in_zones[0] : null;
      if (z) return this._zn(String(z).replace(/^zone\./, ""));
      if (s.state !== "not_home") return this._zn(s.state);
    }
    const z = this._st(this._sid("zona"), this._sid("zona_attuale"), "sensor.megane_zona_attuale");
    return z ? this._txt(z) : null;
  }
  /** indirizzo corrente: attributi del tracker (companion/Android) o stessi dati della pagina Viaggi */
  _addrName() {
    for (const id of [
      this._ov("location"),
      `device_tracker.${this._slug(this._cfg.name)}_posizione`,
      this._car("device_tracker", "location"),
      this._car("device_tracker", ""),
    ]) {
      const s = id ? this._hass.states[id] : null;
      if (!s) continue;
      const v = this._attrAny(s, ["address", "geocoded_location", "place", "location_name", "street"]);
      if (v) return String(v);
    }
    // ripiego: ultimo luogo noto dai viaggi (stessa fonte usata nella pagina Viaggi)
    for (const id of [this._sid("ultimo_trip"), this._sid("viaggi_recenti"), this._sid("archivio_viaggi")]) {
      const s = this._hass.states[id];
      if (!s) continue;
      const trips = Array.isArray(s.attributes.trips) ? s.attributes.trips : [];
      const t = trips.length ? trips[trips.length - 1] : s.attributes;
      const v = this._attrAny(s, ["luogo_arrivo", "luogo_partenza", "indirizzo", "via"])
        || (t && (t.luogo_arrivo || t.luogo_partenza));
      if (v) return String(v);
    }
    const p = this._hass.states[this._sid("posizione")];
    const a = p && this._attrAny(p, ["indirizzo", "luogo", "address", "via"]);
    return a ? String(a) : "";
  }
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
    const v = this._spesaTeo(km) - costo;
    return Math.round((v + Number.EPSILON) * 100) / 100;
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
          <div><b>Renault EV<br>Center</b><span class="ver">v${REC_VER}</span><small>${c.name} · live</small></div>
        </div>
        <div class="nav" id="nav">
          ${NAV.map(([id, em, label]) => `<button data-p="${id}" class="${id === this._page ? "active" : ""}"><span class="em">${em}</span> ${label}</button>`).join("")}
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
    this.shadowRoot.querySelectorAll("[data-palette]").forEach((b) => {
      b.addEventListener("click", () => this._theme_(b.dataset.palette));
    });
    // comandi / bottoni
    this.shadowRoot.querySelectorAll("[data-cmd]").forEach((el) => {
      el.addEventListener("click", () => this._cmd(el.dataset.cmd, el));
    });
    // filtri data viaggi: ricalcola subito la tabella
    this.shadowRoot.querySelectorAll("[data-tfd]").forEach((inp) => {
      inp.addEventListener("change", () => this._update());
    });
    // click sui sensori KPI → apre il more-info di HA
    this.shadowRoot.addEventListener("click", (ev) => {
      const del = ev.target && ev.target.closest ? ev.target.closest("[data-mdel]") : null;
      if (del) {
        this._call("renault_ev_center", "delete_maintenance",
          { maintenance_id: parseInt(del.dataset.mdel, 10) }, "🗑 Intervento eliminato");
        return;
      }
      const target = ev.target && ev.target.closest ? ev.target.closest("[data-more], [data-f]") : null;
      if (!target) return;
      const key = target.dataset.more || target.dataset.f;
      const eid = this._ent(key);
      if (eid) this._moreInfo(eid);
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
    // select filtri storico (entità select.* Renault)
    this.shadowRoot.querySelectorAll("select[data-sel]").forEach((sel) => {
      sel.dataset.ent = this._field(sel.dataset.sel);
      sel.addEventListener("change", () => {
        if (!sel.dataset.ent || !sel.value) return;
        this._call("select", "select_option", { entity_id: sel.dataset.ent, option: sel.value });
      });
    });
    // time: orari carica programmata / promemoria
    this.shadowRoot.querySelectorAll("input[data-time]").forEach((inp) => {
      inp.dataset.ent = this._field(inp.dataset.time);
      inp.addEventListener("change", () => {
        const eid = inp.dataset.ent;
        if (!eid || !inp.value) return;
        const [hh, mm] = inp.value.split(":");
        this._call("time", "set_value", { entity_id: eid, time: `${hh}:${mm}:00` });
      });
    });
    // filtri locali viaggi (anno/mese)
    this.shadowRoot.querySelectorAll("[data-tf], [data-tfm], [data-rf], [data-rfm]").forEach((sel) => {
      sel.addEventListener("change", () => this._update());
    });
    // chip giorni schedulazione
    this.shadowRoot.querySelectorAll(".dchip").forEach((el) => {
      el.addEventListener("click", () => el.classList.toggle("on"));
    });
    // input locali (localStorage): prezzo diesel, consumo equivalente, notify, preavviso
    this.shadowRoot.querySelectorAll("input[data-ls]").forEach((inp) => {
      const saved = localStorage.getItem(inp.dataset.ls);
      if (saved !== null && saved !== "") inp.value = saved;
      inp.addEventListener("change", () => { localStorage.setItem(inp.dataset.ls, inp.value); this._update(); });
    });
    // notify salvato localmente → config runtime se non impostato in YAML
    if (!this._cfg.notify) { const nn = localStorage.getItem("rec_notify"); if (nn) this._cfg.notify = nn; }
    this._update();
    this._theme_(this._theme);
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
    this.shadowRoot.querySelectorAll("[data-palette]").forEach((b) => b.classList.toggle("active", b.dataset.palette === t));
  }
  _dur(v, unit) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    let sec = Number(v);
    const u = String(unit || "s").toLowerCase();
    if (u === "h" || u.includes("hour") || u.includes("ora")) sec = v * 3600;
    else if (u.includes("min")) sec = v * 60;
    const s = Math.max(0, Math.round(sec));
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60;
    return (h > 0 ? h + "h " : "") + (m > 0 || h > 0 ? m + "m " : "") + ss + "s";
  }
  /** Wallbox: valori live + slider A + bilanciamento (entità da config, fallback Lektrico) */
  _drawWallbox(root) {
    if (!root.getElementById("p11")) return;
    const S = this;
    const set = (k, v) => root.querySelectorAll(`[data-wb="${k}"]`).forEach((el) => { el.textContent = v; });
    const stMap = { available: "Pronta", charging: "In carica", preparing: "Preparazione",
      suspended: "Pausa", finishing: "Completamento", faulted: "Errore", idle: "Inattiva",
      connected: "Connesso", disconnected: "Disconnesso", completed: "Completa",
      error: "Errore", need_auth: "Connesso, attesa", paused: "Pausa", locked: "Bloccata" };

    const stateEnt = S._st(S._ov("wallbox_state"), "sensor.wallbox_charger_state");
    set("state", stateEnt ? (stMap[stateEnt.state] || stateEnt.state) : "—");

    const power = S._num(S._ov("wallbox_power"), S._sid("wallbox_potenza"), "sensor.wallbox_instant_power");
    set("power", power === null ? "—" : S._fmt(power) + " kW");
    const cur = S._num("sensor.wallbox_current");
    set("current", cur === null ? "—" : S._fmt(cur, 1) + " A");
    const volt = S._num("sensor.wallbox_voltage");
    set("voltage", volt === null ? "—" : S._fmt(volt, 0) + " V");
    const temp = S._num("sensor.wallbox_temperature");
    set("temp", temp === null ? "—" : S._fmt(temp, 1) + " °C");
    const lim = S._st("sensor.wallbox_limit_reason");
    set("limit", lim ? lim.state : "—");

    const skwh = S._num(S._ov("wallbox_session_energy"), "sensor.wallbox_session_energy");
    set("session_kwh", skwh === null ? "—" : S._fmt(skwh, 2) + " kWh");
    const stEnt = S._st(S._ov("wallbox_session_time"), S._sid("wallbox_tempo_sessione"), "sensor.wallbox_charging_time");
    const stime = S._num(S._ov("wallbox_session_time"), S._sid("wallbox_tempo_sessione"), "sensor.wallbox_charging_time");
    set("session_time", stime === null ? "—" : S._dur(stime, stEnt ? stEnt.attributes.unit_of_measurement : "s"));
    const tot = S._num(S._ov("wallbox_total_energy"), "sensor.wallbox_total_charged_energy");
    set("total_kwh", tot === null ? "—" : S._fmt(tot, 1) + " kWh");

    // slider ampere (number di config, fallback Lektrico)
    const eid = S._ov("wallbox_max_current") || "number.wallbox_user_limit";
    const sNum = S._hass.states[eid];
    const sl = root.getElementById("wb_amp");
    if (sl && sNum) {
      const a = sNum.attributes || {};
      if (a.min !== undefined) sl.min = a.min;
      if (a.max !== undefined) sl.max = a.max;
      if (a.step !== undefined) sl.step = a.step;
      if (parseFloat(sNum.state)) sl.value = sNum.state;
      root.getElementById("wb_amp_val").textContent = `${S._fmt(parseFloat(sNum.state), 0)} A (min ${a.min ?? "?"} · max ${a.max ?? "?"} A)`;
    } else if (sl) {
      root.getElementById("wb_amp_val").textContent = "Nessun number corrente wallbox in configurazione";
    }

    // bilanciamento solare (switch integrazione + ultimo stato dal sensore potenza)
    const balEnt = S._swid("bilanciamento_solare");
    const balSw = S._hass.states[balEnt];
    const bBtn = root.querySelector('[data-cmd="wb_bal_toggle"]');
    if (bBtn) bBtn.textContent = balSw && balSw.state === "on"
      ? "☀️ Bilanciamento solare: ATTIVO" : "☀️ Bilanciamento solare: spento";
    const ps = S._st(S._sid("wallbox_potenza"));
    const bAttr = (k) => { const v = ps ? S._attrAny(ps, [k]) : null; return v === null || v === undefined ? "—" : v; };
    set("bal_surplus", bAttr("surplus_w"));
    set("bal_grid", bAttr("rete_w"));
    set("bal_amps", bAttr("ampere_impostati"));
    set("bal_ts", bAttr("bilanciamento_ultimo_aggiustamento"));

    // bilanciamento casalingo: automazioni HA per nome
    const host = root.querySelector('[data-c="wb-home-autos"]');
    if (host) {
      const ids = ["automation.regola_potenza_wallbox_se_consumo_elevato",
                   "automation.ripristina_potenza_wallbox_se_consumo_basso"];
      let found = ids.map((id) => S._hass.states[id]).filter(Boolean);
      if (!found.length) {
        found = Object.values(S._hass.states)
          .filter((s) => s.entity_id.startsWith("automation.")
            && /wallbox/i.test(s.entity_id + " " + (s.attributes.friendly_name || "")))
          .sort((a, b) => String(a.attributes.friendly_name || a.entity_id)
            .localeCompare(String(b.attributes.friendly_name || b.entity_id), "it"));
      }
      host.innerHTML = found.map((s) =>
        `<div class="cmd" data-cmd="switch" data-ent="${s.entity_id}"><span class="em">${s.state === "on" ? "🟢" : "⚪"}</span>${s.attributes.friendly_name || s.entity_id}<b>${s.state === "on" ? "attiva" : "spenta"}</b></div>`).join("")
        || `<div style="color:var(--muted);font-size:12px">Nessuna automazione "potenza wallbox" trovata — creala in Impostazioni → Automazioni.</div>`;
      host.querySelectorAll("[data-cmd]").forEach((el) =>
        el.addEventListener("click", () => S._cmd(el.dataset.cmd, el)));
    }
  }
  /** Elenco delle automazioni attive (Renault / Wallbox / Bilanciamento). */
  _drawAutos(root) {
    const host = root.querySelector('[data-c="autos-on"]');
    if (!host) return;
    const list = Object.values(this._hass.states)
      .filter((s) => s.entity_id.startsWith("automation.") && s.state === "on"
        && /renault|wallbox|bilanc/i.test(s.entity_id + " " + (s.attributes.friendly_name || "")))
      .sort((a, b) => String(a.attributes.friendly_name || a.entity_id)
        .localeCompare(String(b.attributes.friendly_name || b.entity_id), "it"));
    host.innerHTML = list.length
      ? list.map((s) => `<div class="row"><span>🟢 ${s.attributes.friendly_name || s.entity_id}</span></div>`).join("")
      : `<div style="color:var(--muted);font-size:12px">Nessuna automazione attiva (Renault/Wallbox/Bilanciamento).</div>`;
  }
  /** Toggle on/off delle automazioni create (pagina Automazioni). */
  /** icona per automazione creata, dedotta dall'alias */
  _autoIcon(txt) {
    const t = String(txt).toLowerCase();
    if (/scadenz|assicur|bollo|revision/.test(t)) return "🛡️";
    if (/completat|fine ricarica/.test(t)) return "🔋";
    if (/avvio|avvia/.test(t)) return "⚡";
    if (/batteria bassa|low/.test(t)) return "⚠️";
    if (/riassunt|giornalier/.test(t)) return "📊";
    if (/clima|condizion|ac\b/.test(t)) return "❄️";
    if (/bilanciament|solar/.test(t)) return "☀️";
    if (/programma|ricarica/.test(t)) return "⏰";
    return "🤖";
  }
  _drawAutoToggles(root) {
    const host = root.querySelector('[data-c="autos-created"]');
    if (!host) return;
    const S = this;
    const list = Object.values(S._hass.states)
      .filter((s) => s.entity_id.startsWith("automation.")
        && /renault_ev_center|renault|wallbox|bilanc/i.test(s.entity_id + " " + (s.attributes.friendly_name || "")))
      .sort((a, b) => String(a.attributes.friendly_name || a.entity_id)
        .localeCompare(String(b.attributes.friendly_name || b.entity_id), "it"));
    host.innerHTML = list.length
      ? list.map((s) => {
        const nome = s.attributes.friendly_name || s.entity_id;
        return `<div class="row"><span>${S._autoIcon(nome + " " + s.entity_id)} ${nome}</span><label class="switch"><input type="checkbox" ${s.state === "on" ? "checked" : ""} data-auto="${s.entity_id}"><span></span></label></div>`;
      }).join("")
      : `<div style="color:var(--muted);font-size:12px">Nessuna automazione Renault trovata. Usa "Crea automazioni consigliate" in Impostazioni.</div>`;
    host.querySelectorAll("[data-auto]").forEach((el) => el.addEventListener("change", () =>
      S._call("homeassistant", el.checked ? "turn_on" : "turn_off", { entity_id: el.dataset.auto },
        el.checked ? "Automazione attivata" : "Automazione disattivata")));
  }
  _cmd(cmd, el) {
    const n = this._slug(this._cfg.name);
    const D = "renault_ev_center";
    switch (cmd) {
      case "ac": {
        const cl = this._st(
          this._ov("ac_button"),
          this._ov("climate"),
          this._car("climate", ""),
          "button.start_air_conditioner",
          this._car("button", "start_air_conditioner"),
          this._car("button", "avviare_il_condizionatore_d_aria"),
          this._sid("climatizzatore"),
        );
        if (cl && cl.entity_id.startsWith("climate.")) this._call("climate", "set_temperature", { entity_id: cl.entity_id, temperature: 21 }, "❄️ A/C: 21 °C");
        else if (cl && cl.entity_id.startsWith("button.")) this._call("button", "press", { entity_id: cl.entity_id }, "❄️ A/C avviata");
        else this._toast("⚠️ Nessun comando A/C dell'auto trovato");
        break;
      }
      case "charge": {
        // comando dell'AUTO (app Renault): avvia la ricarica lato veicolo
        const b = this._st(
          this._ov("start_charge"),
          this._car("button", "start_charge"),
          this._car("button", "avviare_la_ricarica"),
          "button.start_charge",
          this._ov("wb_charge_switch"),
          "button.wallbox_charger_start",
        );
        if (!b) { this._toast("⚠️ Nessun avvio carica trovato (mappa 'Pulsante Avvia carica' in Configura)"); break; }
        const dom = String(b.entity_id).split(".")[0];
        if (dom === "switch") this._call("switch", "turn_on", { entity_id: b.entity_id }, "⚡ Avvia carica");
        else if (dom === "button") this._call("button", "press", { entity_id: b.entity_id }, "⚡ Avvia carica (auto)");
        else this._call("homeassistant", "turn_on", { entity_id: b.entity_id }, "⚡ Avvia carica");
        break;
      }
      case "close_trip": this._call(D, "close_trip", {}, "🏁 Viaggio chiuso"); break;
      case "openmap": this._moreInfo(this._car("device_tracker", "posizione") || "device_tracker.megane_posizione"); break;
      case "csv": this._call(D, "export_trips_csv", {}, "📥 CSV esportato"); break;
      case "create_automations": this._call(D, "create_automations", {}, "✨ Automazioni create"); break;
      case "schsave_ricarica": this._saveSchedule("ricarica"); break;
      case "schsave_clima": this._saveSchedule("clima"); break;
      case "schsave_promemoria": this._saveSchedule("promemoria"); break;
      case "maint_tagliando": this._saveMaint("tagliando"); break;
      case "maint_gomme": this._saveMaint("gomme"); break;
      case "maint_add": this._addMaint(); break;
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
      case "wb_start": {
        const b = this._st(this._ov("wb_charge_switch"), "button.wallbox_charger_start");
        if (!b) { this._toast("⚠️ Comando avvio wallbox non trovato (configura la wallbox)"); break; }
        if (b.entity_id.startsWith("switch.")) this._call("switch", "turn_on", { entity_id: b.entity_id }, "🔌 Ricarica avviata");
        else this._call("button", "press", { entity_id: b.entity_id }, "🔌 Ricarica avviata");
        break;
      }
      case "wb_stop": {
        const b = this._st("button.wallbox_charge_stop", this._ov("wb_charge_switch"));
        if (!b) { this._toast("⚠️ Comando stop wallbox non trovato"); break; }
        if (b.entity_id.startsWith("switch.")) this._call("switch", "turn_off", { entity_id: b.entity_id }, "⏹️ Ricarica fermata");
        else this._call("button", "press", { entity_id: b.entity_id }, "⏹️ Ricarica fermata");
        break;
      }
      case "wb_set_current": {
        const eid = this._ov("wallbox_max_current") || "number.wallbox_user_limit";
        const inp = this.shadowRoot.getElementById("wb_amp");
        const v = inp ? parseFloat(inp.value) : null;
        if (v) this._call("number", "set_value", { entity_id: eid, value: v }, `🔌 Limite corrente: ${v} A`);
        break;
      }
      case "wb_bal_toggle": {
        const eid = this._swid("bilanciamento_solare");
        const s = this._hass.states[eid];
        if (!s) { this._toast("⚠️ Switch bilanciamento solare non trovato"); break; }
        this._call("homeassistant", s.state === "on" ? "turn_off" : "turn_on", { entity_id: eid }, "☀️ Bilanciamento solare");
        break;
      }
      case "horn": {
        const b = this._st(this._ov("horn"), this._ov("horn_button"), this._car("button", "sound_horn"), "button.megane_sound_horn");
        if (b) this._call("button", "press", { entity_id: b.entity_id }, "📣 Clacson");
        else this._toast("⚠️ Clacson non mappato (Configura → Comandi)");
        break;
      }
      case "flash": {
        const b = this._st(this._ov("light"), this._ov("flash_button"), this._car("button", "flash_lights"), "button.megane_flash_lights");
        if (!b) { this._toast("⚠️ Luci non mappate (Configura → Comandi)"); break; }
        const d = String(b.entity_id).split(".")[0];
        if (d === "light") this._call("light", "toggle", { entity_id: b.entity_id }, "💡 Luci");
        else if (d === "switch") this._call("switch", "toggle", { entity_id: b.entity_id }, "💡 Luci");
        else this._call("button", "press", { entity_id: b.entity_id }, "💡 Luci lampeggianti");
        break;
      }
      case "lowsave": {
        const giorni = [...this.shadowRoot.querySelectorAll("[data-lowday].on")].map((e) => e.dataset.lowday);
        this._call("renault_ev_center", "set_low_soc_days", { giorni }, "🔔 Giorni avviso salvati");
        break;
      }
      case "tfilter-reset": {
        const f = this.shadowRoot.querySelector('[data-tfd="from"]');
        const t = this.shadowRoot.querySelector('[data-tfd="to"]');
        if (f) f.value = "";
        if (t) t.value = "";
        this._update();
        break;
      }
      case "charge_stop": {
        const b = this._st(this._ov("wb_stop_switch"), this._car("button", "stop_charge"), "button.wallbox_charger_stop");
        if (!b) { this._toast("⚠️ Stop carica non mappato (Configura → Wallbox)"); break; }
        const d = String(b.entity_id).split(".")[0];
        if (d === "switch") this._call("switch", "turn_off", { entity_id: b.entity_id }, "⏹ Stop carica");
        else this._call("button", "press", { entity_id: b.entity_id }, "⏹ Stop carica");
        break;
      }
    }
  }

  // ------------------------------------------------------------- aggiornamento valori
  _update() {
    const root = this.shadowRoot;
    // barra batteria
    const b = this._field("batt");
    const bar = root.querySelector('[data-b="battbar"]');
    if (bar) {
      bar.style.width = `${b === null ? 0 : Math.min(100, Math.max(0, b))}%`;
      bar.style.background = b === null ? "var(--line)" : b < 20 ? "var(--bad)" : b < 45 ? "var(--warn)" : "var(--accent)";
    }
    root.querySelectorAll("[data-f]").forEach((el) => {
      if (el.tagName === "INPUT") return; // gli input data-ls si inizializzano in _build
      if (el.dataset.dec) {
        const raw = this._field(el.dataset.f);
        const num = typeof raw === "number" ? raw : parseFloat(raw);
        el.textContent = (num === null || num === undefined || isNaN(num)) ? "—" : this._fmt(num, parseInt(el.dataset.dec, 10));
      } else {
        el.textContent = this._f(el.dataset.f);
      }
      el.classList.toggle("clk", !!this._ent(el.dataset.f));
    });
    const mapSvg = root.querySelector("#evmap");
    if (mapSvg && (!this._mapTs || Date.now() - this._mapTs > 300000)) {
      this._mapTs = Date.now();
      this._drawMap();
    }
    root.querySelectorAll("[data-sw]").forEach((el) => {
      if (el.tagName === "INPUT") { const s = this._hass.states[el.dataset.ent]; el.checked = !!s && s.state === "on"; }
    });
    // avviso batteria bassa: giorni correnti dall'attributo dello switch
    const _lowSw = this._hass.states[this._field("sw_low")];
    const _lowDays = (_lowSw && Array.isArray(_lowSw.attributes.giorni)) ? _lowSw.attributes.giorni : [];
    root.querySelectorAll("[data-lowday]").forEach((el) => {
      el.classList.toggle("on", _lowDays.includes(el.dataset.lowday));
    });
    // chips stato
    const chipLoc = root.querySelector('[data-c="loc"]');
    if (chipLoc) chipLoc.textContent = `📍 ${this._f("loc")}`;
    const chipCh = root.querySelector('[data-c="charging"]');
    if (chipCh) {
      const on = this._chargeOn();
      chipCh.textContent = on ? "🔌 In carica" : "🔓 Non in carica";
      chipCh.className = `chip ${on ? "ok" : ""}`;
    }
    const chipPlug = root.querySelector('[data-c="plug"]');
    if (chipPlug) chipPlug.textContent = this._plugOn() ? "🔗 Collegata" : "🔗 Scollegata";
    const chargeStatus = root.querySelector('[data-c="chargestatus"]');
    if (chargeStatus) chargeStatus.textContent = this._chargeOn() ? "In carica" : "Non in carica";
    // foto auto
    const img = root.querySelector('[data-c="carimg"]');
    if (img) {
      img.innerHTML = this._cfg.image
        ? `<img src="${this._cfg.image}" alt="${this._cfg.name}" onerror="this.parentNode.innerHTML='<div class=\\'ph\\'>🚗</div>'">`
        : `<div class="ph">🚗</div>`;
    }
    // comandi: valori
    const setV = (attr, val) => root.querySelectorAll(`[data-v="${attr}"]`).forEach((el) => { el.textContent = val; });
    setV("cmd_charge", this._chargeOn() ? "In carica" : "Non in carica");
    setV("cmd_plug", this._plugOn() ? "Collegata" : "Scollegata");
    setV("cmd_zona", this._zoneName() || "—");
    setV("cmd_addr", this._addrName() || "—");
    setV("cmd_tipo", this._f("tipo_ric"));
    setV("cmd_tempo", this._f("tempo_ric"));
    setV("cmd_ora", this._f("ora_compl"));
    setV("cmd_wb", this._wb_state_txt());
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
    root.querySelectorAll("input[data-time]").forEach((inp) => {
      if (document.activeElement === inp) return;
      const s = this._hass.states[inp.dataset.ent];
      if (s && typeof s.state === "string") {
        const [hh, mm] = s.state.split(":");
        inp.value = hh ? `${hh}:${mm ?? "00"}` : "";
      }
    });
    // select filtri: opzioni + valore corrente
    root.querySelectorAll("select[data-sel]").forEach((sel) => {
      const s = this._hass.states[sel.dataset.ent];
      const opts = (s && Array.isArray(s.attributes.options)) ? s.attributes.options : [];
      const sig = opts.join("|");
      if (sel.dataset.sig !== sig) {
        sel.dataset.sig = sig;
        sel.innerHTML = opts.map((o) => `<option>${o}</option>`).join("") || `<option>—</option>`;
      }
      if (s && s.state !== "unavailable") sel.value = s.state;
    });
    // righe lista da attributo (consumo_per_zona ecc.)
    root.querySelectorAll("[data-attr-list]").forEach((tb) => {
      const rows = this._list(this._sid(tb.dataset.attrList));
      tb.innerHTML = rows.slice(0, 8).map((r) =>
        `<tr><td>${r.zona ?? r.nome ?? r.rotta ?? r.tipo ?? "—"}</td><td>${r.viaggi ?? r.n ?? "—"}</td>
        <td>${this._fmt(parseFloat(r.km ?? 0), 1)}</td>
        <td><span class="badge">${this._fmt(parseFloat(r.kwh_100km ?? r.efficienza ?? r.eff ?? 0), 1)}</span></td></tr>`).join("")
        || `<tr><td colspan="4" style="color:var(--muted)">Nessun dato</td></tr>`;
    });
    this._tableRotte(root);
    this._drawWallbox(root);
    this._drawAutos(root);
    this._drawAutoToggles(root);
    // tabella scadenze (attributo scadenze di prossima_scadenza)
    const tbSc = root.querySelector('[data-c="tab-scadenze"]');
    if (tbSc) {
      const s = this._st(this._sid("prossima_scadenza"));
      const rs = (s && Array.isArray(s.attributes.scadenze) ? s.attributes.scadenze : []);
      tbSc.innerHTML = rs.slice(0, 6).map((r) =>
        `<tr><td>${r.tipo ?? r.nome ?? "—"}</td><td><b>${r.giorni ?? r.gg ?? "—"}</b> gg</td></tr>`).join("")
        || `<tr><td colspan="2" style="color:var(--muted)">Nessuna scadenza</td></tr>`;
    }
    // celle percorrenza: [data-per="oggi|usati"] → riga attributo `righe`
    root.querySelectorAll("[data-per]").forEach((el) => {
      const [per, key] = el.dataset.per.split("|");
      const rows = this._list(this._sid("percorrenza"));
      const r = rows.find((x) => this._slug(String(x.nome ?? "")) === per);
      const v = r ? parseFloat(r[key]) : NaN;
      el.textContent = isNaN(v) ? "—" : (key === "km" ? this._i(v) + " km" : this._fmt(v, 2) + " kWh");
    });
    // tabella storico tagliandi
    const tbTag = root.querySelector('[data-c="tab-tagliandi"]');
    if (tbTag) {
      const rows = this._list(this._sid("tagliandi"));
      tbTag.innerHTML = rows.slice(0, 12).map((r) =>
        `<tr><td>${this._d(r.data)}</td><td>${this._i(parseFloat(r.km) || 0)}</td><td>${r.tipo ?? "—"}</td><td><b>${this._fmt(parseFloat(r.costo ?? r.euro ?? 0), 0)} €</b></td><td><span class="dchip" data-mdel="${r.id}" title="Elimina">🗑</span></td></tr>`).join("")
        || `<tr><td colspan="5" style="color:var(--muted)">Nessun intervento registrato</td></tr>`;
    }
    // righe top/stop da attributi oggetto: [data-topstop="migliore|kwh_per_100km"]
    root.querySelectorAll("[data-topstop]").forEach((el) => {
      const [key, sub] = el.dataset.topstop.split("|");
      const s = this._st(this._sid("viaggio_top_stop_del_mese"));
      const o = s ? s.attributes[key] : null;
      const v = o ? o[sub] : null;
      el.textContent = v === undefined || v === null ? "—" : this._fmt(parseFloat(v), 1);
    });
    // grafico 7 giorni (apexcharts se installato, altrimenti barre native del pannello)
    this._drawKmChart(root);
    // tabelle dati dinamici
    this._tableViaggi(root);
    this._tableRicariche(root);
    this._tableSalute(root);
    this._tableMesi(root);
    this._treeViaggi(root);
    this._tileStats(root);
    this._drawSeasons(root);
    this._rowsAttr(root);
  }
  _addMaint() {
    const root = this.shadowRoot;
    const g = (k) => root.querySelector(`[data-ma="${k}"]`);
    const data = g("data") && g("data").value ? g("data").value : "";
    const km = g("km") && g("km").value ? parseFloat(g("km").value) : undefined;
    const costo = g("costo") && g("costo").value ? parseFloat(g("costo").value) : 0;
    const tipo = (g("tipo") && g("tipo").value) || "Tagliando";
    const payload = { data, tipo, costo, note: "" };
    if (km !== undefined && !isNaN(km)) payload.km = km;
    this._call("renault_ev_center", "add_maintenance", payload, "➕ Intervento registrato");
  }
  _saveMaint(tipo) {
    const root = this.shadowRoot;
    const kmEl = root.querySelector(`input[data-mk="${tipo}"]:not([data-mdate])`);
    const dEl = root.querySelector(`input[data-mk="${tipo}"][data-mdate]`);
    const km = kmEl && kmEl.value ? parseFloat(kmEl.value) : undefined;
    const data = dEl && dEl.value ? dEl.value : "";
    const payload = { tipo, data };
    if (km !== undefined && !isNaN(km)) payload.km = km;
    this._call("renault_ev_center", "set_maintenance", payload, `💾 Scadenza ${tipo} salvata`);
  }
  _saveSchedule(tipo) {
    const root = this.shadowRoot;
    const g = (k) => root.querySelector(`[data-sch="${tipo}"][data-k="${k}"]`);
    const on = root.querySelector(`input[data-schon="${tipo}"]`);
    const giorni = [...root.querySelectorAll(`[data-schday^="${tipo}|"].on`)]
      .map((e) => e.dataset.schday.split("|")[1]);
    const d = {
      tipo,
      attivo: on ? on.checked : true,
      inizio: (g("inizio") && g("inizio").value) || "23:30",
      fine: (g("fine") && g("fine").value) || "07:00",
      soc: (g("soc") && parseInt(g("soc").value, 10)) || 80,
      modo: (g("modo") && g("modo").value) || "cool",
      temperatura: (g("temperatura") && parseInt(g("temperatura").value, 10)) || 21,
      giorni,
    };
    this._call("renault_ev_center", "set_schedule", d, `⏰ Schedulazione ${tipo} salvata`);
  }
  async _drawMap() {
    const box = this.shadowRoot && this.shadowRoot.querySelector("#evmap");
    if (!box || this._mapCard) return;
    const loc = this._ov("location") || this._car("device_tracker", "posizione") || "device_tracker.megane_posizione";
    if (typeof window.loadCardHelpers !== "function") return;
    try {
      const helpers = await window.loadCardHelpers();
      const card = helpers.createCardElement({
        type: "map",
        entities: [{ entity: loc }],
        hours_to_show: 48,
        theme_mode: "dark",
        auto_fit: false,
        default_zoom: 11,
      });
      card.hass = this._hass;
      card.style.display = "block";
      card.style.height = "100%";
      box.innerHTML = "";
      box.appendChild(card);
      this._mapCard = card;
    } catch (e) {
      box.innerHTML = `<div style="display:flex;height:100%;align-items:center;justify-content:center;color:var(--muted);font-size:12px">Mappa non disponibile</div>`;
    }
  }
  /**
   * Grafico "Km percorsi (7 giorni)".
   * Con apexcharts-card installata rende il grafico completo (colonne km + linea consumi,
   * come da config utente); altrimenti ripiega sulle barre native del pannello.
   */
  async _drawKmChart(root) {
    const box = root.querySelector("#kmchart");
    if (!box) return;
    const hasApex = typeof customElements !== "undefined" && !!customElements.get("apexcharts-card");
    if (!hasApex) { this._noApexNotice(box); return; }
    if (this._kmChart) { this._kmChart.hass = this._hass; return; }
    // se prima era attivo il fallback nativo, rimuovi la sua intestazione
    box.parentElement && box.parentElement.querySelectorAll("[data-c='bars7-head']")
      .forEach((el) => el.remove());
    if (typeof window.loadCardHelpers !== "function") return;
    try {
      const helpers = await window.loadCardHelpers();
      const card = helpers.createCardElement({
        type: "custom:apexcharts-card",
        graph_span: "7d",
        span: { end: "day" },
        update_interval: "10min",
        apex_config: { enabled: true, autoScaleYaxis: false, chart: { height: "200px" } },
        yaxis: [
          { id: "first", min: 0, decimals: 0 },
          { id: "second", opposite: true, decimals: 1 },
        ],
        series: [
          {
            entity: this._sid("km_giornalieri"),
            name: "Km Percorsi",
            type: "column",
            yaxis_id: "first",
            curve: "smooth",
            stroke_width: 2,
            fill_raw: "last",
            color: "#ff9933",
            extend_to: "end",
            min: 0,
            float_precision: 0,
            group_by: { func: "max", fill: "zero", duration: "1day" },
            show: { legend_value: false },
          },
          {
            entity: this._sid("kwh_per_100km"),
            name: "Media Consumi",
            yaxis_id: "second",
            curve: "smooth",
            stroke_width: 3,
            fill_raw: "last",
            color: "green",
            extend_to: "end",
            float_precision: 2,
            min: 0,
            group_by: { func: "avg", fill: "last", duration: "1day" },
            show: { legend_value: false },
          },
        ],
        header: { show: true, show_states: true },
        all_series_config: { stroke_width: 1, show: { extremas: true } },
      });
      card.hass = this._hass;
      card.style.display = "block";
      box.innerHTML = "";
      box.appendChild(card);
      this._kmChart = card;
    } catch (e) {
      this._noApexNotice(box);
    }
  }
  /** apexcharts-card assente (o in errore): solo avviso, nessun grafico alternativo */
  _noApexNotice(box) {
    box.style.cssText = "";
    box.innerHTML =
      `<div style="padding:16px;border:1px dashed var(--accent);border-radius:12px;background:rgba(255,255,255,.04)">
        <div style="font-weight:700;margin-bottom:6px">📦 Serve la card «apexcharts-card»</div>
        <div style="font-size:13px;color:var(--muted);line-height:1.7">
          Per vedere questo grafico installa da <b>HACS → Frontend</b> → <code>apexcharts-card</code>,
          poi riavvia Home Assistant e ricarica la pagina.
        </div></div>`;
  }
  _wb_state_txt() {
    const p = this._num(this._sid("wallbox_potenza"), "sensor.wallbox_instant_power", this._car("sensor", "battery_charger_power"));
    if (p !== null) return p > 0 ? `${this._fmt(p, 2)} kW` : "Inattiva";
    const b = this._st(this._sid("wallbox"), `binary_sensor.wallbox_${this._cfg.car}`, this._car("binary_sensor", "wallbox"), this._car("binary_sensor", "charging"));
    if (!b) return "—";
    const v = this._slug(b.state);
    return v === "on" || v === "charging" || v === "in_carica" ? "Wallbox attiva" : "Scollegata";
  }
  _last7() {
    const cands = [this._sid("storico_giornaliero"), this._sid("trip_history"), "sensor.megane_trip_history"];
    let arr = this._list(...cands);
    if (!arr.length) {
      for (const id of cands) {
        const s = this._hass.states[id];
        const vals = s && s.attributes ? Object.values(s.attributes).filter((v) => v && typeof v === "object") : [];
        if (vals.length) { arr = vals; break; }
      }
    }
    const out = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date(Date.now() - i * 86400000);
      const key = d.toISOString().slice(0, 10);
      const row = arr.find((r) => String(r.data || r.giorno || r.date || r.name || "").startsWith(key));
      const km = row ? parseFloat(row.km ?? row.km_percorsi ?? row.chilometri ?? 0) || 0 : 0;
      const kwh = row ? parseFloat(row.kwh ?? row.kwh_consumati ?? 0) || 0 : 0;
      const eff = row ? parseFloat(row.kwh_per_100km ?? row.efficienza ?? row.eff ?? 0) || 0 : 0;
      const pct = row ? parseFloat(row.pct ?? row.batteria_pct ?? 0) || 0 : 0;
      out.push({ label: d.toLocaleDateString("it-IT", { weekday: "narrow" }), km, kwh, eff, pct });
    }
    return out;
  }
  _drawBars(box, data) {
    if (!box) return;
    const max = Math.max(1, ...data.map((d) => d.km));
    const totKwh = data.reduce((a, d) => a + d.kwh, 0);
    const totKm = data.reduce((a, d) => a + d.km, 0);
    const media = totKm > 0 && totKwh > 0 ? totKm / totKwh : 0;
    box.parentElement.querySelectorAll("[data-c='bars7-head']").forEach((el) => el.remove());
    const head = document.createElement("div");
    head.dataset.c = "bars7-head";
    head.style.cssText = "font-size:11.5px;color:var(--muted);margin-bottom:8px";
    head.textContent = `7 giorni: ${this._i(totKm)} km · ${this._fmt(totKwh, 1)} kWh` +
      (media > 0 ? ` · media ${this._fmt(media, 2)} km/kWh` : "");
    box.parentElement.insertBefore(head, box);
    box.innerHTML = data.map((d) => {
      const h = d.km > 0 ? Math.round((d.km / max) * 100) : 2;
      const tip = `${d.km} km · ${this._fmt(d.kwh, 2)} kWh · ${this._fmt(d.eff, 1)} kWh/100km${d.pct ? " · " + d.pct + "% usata" : ""}`;
      return `<div title="${tip}" style="flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:3px;height:100%">
        <span style="font-size:10px;font-weight:700;color:var(--txt)">${d.km > 0 ? Math.round(d.km) : ""}</span>
        <div style="width:100%;background:var(--accent);opacity:.85;border-radius:4px 4px 0 0;height:${h}%"></div>
        <span style="font-size:10px;color:var(--muted)">${d.label}</span></div>`;
    }).join("");
  }
  _rowsOf(state, keys) {
    const list = this._list(state ? state.entity_id : "");
    return list;
  }
  _tableRotte(root) {
    const tb = root.querySelector('[data-c="tab-rotte"]');
    if (!tb) return;
    const trips = this._list(this._sid("archivio_viaggi"), this._sid("viaggi_recenti"));
    const selY = root.querySelector('[data-rf="year"]');
    const selM = root.querySelector('[data-rfm="month"]');
    const years = [...new Set(trips.map((r) => String(r.data || "").slice(0, 4)).filter(Boolean))].sort().reverse();
    if (selY && (selY.dataset.sig || "") !== years.join("|")) {
      selY.dataset.sig = years.join("|");
      const cur = selY.value;
      selY.innerHTML = `<option value="">Tutti gli anni</option>` + years.map((y) => `<option value="${y}">${y}</option>`).join("");
      selY.value = cur;
    }
    if (selM && !selM.dataset.done) {
      selM.dataset.done = "1";
      selM.innerHTML = `<option value="">Tutti i mesi</option>` + NOMI_MESI.map((n, i) => `<option value="${String(i + 1).padStart(2, "0")}">${n}</option>`).join("");
    }
    const fy = selY ? selY.value : "";
    const fm = selM ? selM.value : "";
    const groups = {};
    trips.forEach((r) => {
      const d = String(r.data || "");
      if (fy && d.slice(0, 4) !== fy) return;
      if (fm && d.slice(5, 7) !== fm) return;
      const key = `${this._zn(r.zona_partenza ?? r.ricarica_precedente)} → ${this._zn(r.zona_arrivo)}`;
      const g = groups[key] = groups[key] || { n: 0, km: 0, kwh: 0, costo: 0 };
      g.n += 1;
      g.km += parseFloat(r.km || 0) || 0;
      g.kwh += Math.abs(parseFloat(r.kwh_consumati ?? r.kwh ?? 0)) || 0;
      g.costo += parseFloat(r.costo_stimato ?? r.costo ?? 0) || 0;
    });
    const rows = Object.entries(groups).sort((a, b) => b[1].km - a[1].km);
    tb.innerHTML = rows.map(([k, g]) => {
      const eff = g.km > 0 ? g.kwh / g.km * 100 : 0;
      return `<tr><td>${k}</td><td>${g.n}</td><td>${this._i(g.km)}</td><td>${this._fmt(g.kwh, 1)}</td>
        <td><span class="badge">${this._fmt(eff, 1)}</span></td><td>${this._fmt(g.costo, 2)} €</td></tr>`;
    }).join("") || `<tr><td colspan="6" style="color:var(--muted)">Nessun dato per il filtro</td></tr>`;
  }
  _tableMesi(root) {
    const box = root.querySelector('[data-c="tab-mesi"]');
    if (!box) return;
    const st = this._st(this._sid("storico_giornaliero"));
    const mesi = st && st.attributes ? st.attributes.mesi : null;
    if (!mesi || !Object.keys(mesi).length) {
      box.innerHTML = `<div style="color:var(--muted)">Nessuno storico mensile ancora</div>`;
      return;
    }
    const now = new Date();
    const curY = String(now.getFullYear());
    const curM = String(now.getMonth() + 1).padStart(2, "0");
    box.innerHTML = Object.keys(mesi).sort().reverse().map((y) => {
      const mm = mesi[y] || {};
      let tC = 0, tK = 0, tKm = 0;
      const rows = NOMI_MESI.map((nome, i) => {
        const m = String(i + 1).padStart(2, "0");
        const r = mm[m];
        const futuro = y > curY || (y === curY && m > curM);
        const c = r ? r.costo : 0, k = r ? r.kwh : 0, km = r ? r.km : 0;
        tC += c; tK += k; tKm += km;
        return `<tr><td>${nome}</td><td>${r ? this._fmt(c, 2) + " €" : (futuro ? "" : "0,00 €")}</td>
          <td>${r ? this._fmt(k, 1) + " kWh" : (futuro ? "" : "0,0 kWh")}</td>
          <td>${r && km ? this._i(km) + " km" : (futuro ? "attesa" : "0 km")}</td></tr>`;
      }).join("");
      return `<details class="anno" open><summary>▼ ${y} <span class="tr">${this._fmt(tC, 2)} € · ${this._fmt(tK, 1)} kWh · ${this._i(tKm)} km</span></summary>
        <table><tr><th>Mese</th><th>Costo</th><th>Ricaricati</th><th>KM</th></tr>${rows}
        <tr class="totrow"><td>TOTALE</td><td>${this._fmt(tC, 2)} €</td><td>${this._fmt(tK, 1)} kWh</td><td>${this._i(tKm)} km</td></tr></table></details>`;
    }).join("");
  }
  _tableViaggi(root) {
    const s = this._st(this._sid("viaggi_recenti"));
    let rows = this._list(s ? s.entity_id : "");
    if (!rows.length) {
      // fallback: core Renault espone sensor.<car>_trip_history.attributes.days
      const th = this._st(this._sid("trip_history"), "sensor.megane_trip_history");
      const days = th && Array.isArray(th.attributes.days) ? th.attributes.days : [];
      rows = days.map((d) => ({
        data: d.date, ora_inizio: null, km: d.km, batteria_delta: d.battery_pct,
        kwh: d.kwh, kwh_per_100km: d.kwh_100, costo_stimato: NaN, zona_partenza: null,
      }));
    }
    const tb = root.querySelector('[data-c="tab-viaggi"]');
    if (!tb) return;
    const selY = root.querySelector('[data-tf="year"]');
    const selM = root.querySelector('[data-tfm="month"]');
    const years = [...new Set(rows.map((r) => String(r.data || "").slice(0, 4)).filter(Boolean))].sort().reverse();
    if (selY && (selY.dataset.sig || "") !== years.join("|")) {
      selY.dataset.sig = years.join("|");
      const cur = selY.value;
      selY.innerHTML = `<option value="">Tutti gli anni</option>` + years.map((y) => `<option value="${y}">${y}</option>`).join("");
      selY.value = cur;
    }
    if (selM && !selM.dataset.done) {
      selM.dataset.done = "1";
      selM.innerHTML = `<option value="">Tutti i mesi</option>` + NOMI_MESI.map((n, i) => `<option value="${String(i + 1).padStart(2, "0")}">${n}</option>`).join("");
    }
    const fy = selY ? selY.value : "";
    const fm = selM ? selM.value : "";
    const from = (root.querySelector('[data-tfd="from"]') || {}).value || "";
    const to = (root.querySelector('[data-tfd="to"]') || {}).value || "";
    const vis = rows.filter((r) => {
      const dd = String(r.data || "");
      if (fy && dd.slice(0, 4) !== fy) return false;
      if (fm && dd.slice(5, 7) !== fm) return false;
      if (from && dd < from) return false;
      if (to && dd > to) return false;
      return true;
    });
    tb.innerHTML = vis.slice(0, 30).map((r) => {
      const eff = r.kwh_per_100km ?? r.efficienza ?? r.eff;
      const d = r.batteria_delta ?? r.delta_soc;
      const soc = (r.batteria_inizio != null && r.batteria_fine != null)
        ? `${Math.round(r.batteria_inizio)}% → ${Math.round(r.batteria_fine)}%`
        : (d !== undefined && d !== null ? d + "%" : "—");
      return `<tr><td>${this._d(r.data)}</td>        <td>${r.stima_orario ? "≈ " : ""}${r.ora_inizio ?? "—"}${r.ora_fine ? "–" + r.ora_fine : ""}</td>
        <td><b>${this._fmt(parseFloat(r.km ?? r.chilometri ?? 0), 1)}</b></td>
        <td>${soc}</td><td>${d !== undefined && d !== null ? d + "%" : "—"}</td><td>${this._fmt(parseFloat(r.kwh_consumati ?? r.kwh ?? 0), 2)}</td>
        <td><span class="badge">${this._fmt(parseFloat(eff ?? 0), 1)}</span></td>
        <td>${this._fmt(parseFloat(r.costo_stimato ?? r.costo ?? 0), 2)} €</td>
        <td>${this._zn(r.zona_partenza ?? r.ricarica_precedente)}${r.luogo_partenza ? `<br><span style="color:var(--muted);font-size:11px">${r.luogo_partenza}${r.paese_partenza ? " · " + r.paese_partenza : ""}</span>` : ""}</td>
        <td>${this._zn(r.zona_arrivo)}${r.luogo_arrivo ? `<br><span style="color:var(--muted);font-size:11px">${r.luogo_arrivo}${r.paese_arrivo ? " · " + r.paese_arrivo : ""}</span>` : ""}</td></tr>`;
    }).join("") || `<tr><td colspan="10" style="color:var(--muted)">Nessun viaggio per il filtro scelto</td></tr>`;
  }
  _tableRicariche(root) {
    const rows = this._list(this._sid("lista_ricariche"));
    const tb = root.querySelector('[data-c="tab-ricariche"]');
    if (!tb) return;
    const vis = rows.slice(0, 8);
    const cells = vis.map((r) => {
      const dm = parseFloat(r.durata_min ?? r.durata ?? 0);
      const dur = dm > 0 ? this._fmt(dm / 60, 1) + " h" : "—";
      const dsoc = (r.soc_end !== undefined && r.soc_start !== undefined) ? "+" + Math.round(r.soc_end - r.soc_start) + "%" : "—";
      return `<tr><td>${this._d(r.data)}${r.ora_inizio ? " · " + r.ora_inizio : ""}</td>
        <td>${r.tipo ?? "—"}</td><td>${dur}</td>
        <td><b>${dsoc}</b></td>
        <td>${this._fmt(parseFloat(r.kwh ?? r.energia ?? 0), 2)}</td>
        <td>${this._fmt(parseFloat(r.potenza_media_kw ?? r.kw_medio ?? 0), 2)}</td>
        <td>${this._fmt(parseFloat(r.kwh > 0 ? r.costo / r.kwh : NaN), 3)}</td>
        <td><b>${this._fmt(parseFloat(r.costo ?? 0), 2)} €</b></td></tr>`;
    });
    if (vis.length) {
      const totKwh = vis.reduce((a, r) => a + (parseFloat(r.kwh ?? r.energia ?? 0) || 0), 0);
      const totCost = vis.reduce((a, r) => a + (parseFloat(r.costo ?? 0) || 0), 0);
      cells.push(`<tr class="totrow"><td colspan="4" style="color:var(--muted);font-weight:700">TOTALE (${vis.length})</td><td><b>${this._fmt(totKwh, 2)}</b></td><td></td><td></td><td><b>${this._fmt(totCost, 2)} €</b></td></tr>`);
    }
    tb.innerHTML = cells.join("") || `<tr><td colspan="8" style="color:var(--muted)">Nessuna ricarica registrata</td></tr>`;
  }
  _tableSalute(root) {
    const rows = this._list(this._sid("lista_ricariche"));
    const tb = root.querySelector('[data-c="tab-salute"]');
    if (!tb) return;
    tb.innerHTML = rows.slice(0, 6).map((r) => {
      const rete = parseFloat(r.rete_kwh ?? r.kwh ?? 0);
      const batt = parseFloat(r.batteria_kwh ?? 0) || (rete > 0 ? NaN : 0);
      const eff = r.efficienza !== undefined ? parseFloat(r.efficienza) : (rete > 0 && !isNaN(batt) ? batt / rete * 100 : NaN);
      const dsoc = (r.soc_end !== undefined && r.soc_start !== undefined) ? "+" + Math.round(r.soc_end - r.soc_start) + "%" : "—";
      return `<tr><td>${this._d(r.data)}</td><td>${dsoc}</td>
        <td>${this._fmt(rete, 2)}</td><td>${this._fmt(batt, 2)}</td>
        <td><span class="badge">${this._fmt(eff, 1)}%</span></td></tr>`;
    }).join("") || `<tr><td colspan="5" style="color:var(--muted)">Nessuna sessione</td></tr>`;
  }
  _treeViaggi(root) {
    const box = root.querySelector('[data-c="tree"]');
    if (!box) return;
    const arch = this._st(this._sid("archivio_viaggi"), this._sid("storico_giornaliero"));
    let rows = this._list(arch ? arch.entity_id : "");
    if (!rows.length) {
      const th = this._st(this._sid("trip_history"), "sensor.megane_trip_history");
      const days = th && Array.isArray(th.attributes.days) ? th.attributes.days : [];
      rows = days.map((d) => ({ data: d.date, km: d.km, kwh_per_100km: d.kwh_100, costo_stimato: null }));
    }
    if (!rows.length) { box.innerHTML = `<div style="color:var(--muted)">Archivio viaggi vuoto</div>`; return; }
    // aggrega per giorno
    const byDay = {};
    rows.forEach((r) => {
      const d = String(r.data || "");
      if (!d) return;
      const g = byDay[d] = byDay[d] || { data: d, km: 0, kwh: 0, peso_eff: 0, n_eff: 0, costo: 0 };
      g.km += parseFloat(r.km || 0) || 0;
      g.kwh += parseFloat(r.kwh_consumati ?? r.kwh ?? 0) || 0;
      const c = parseFloat(r.costo_stimato ?? r.costo ?? 0);
      if (!isNaN(c)) g.costo += c;
      const e = parseFloat(r.kwh_per_100km ?? r.efficienza ?? 0);
      if (!isNaN(e) && e > 0) { g.peso_eff += e; g.n_eff += 1; }
    });
    const days = Object.values(byDay).sort((a, b) => String(b.data).localeCompare(String(a.data)));
    const tree = {};
    days.forEach((r) => {
      const d = String(r.data);
      const y = d.slice(0, 4) || "—", m = d.slice(5, 7) || "—";
      (tree[y] = tree[y] || {})[m] = (tree[y][m] || []).concat(r);
    });
    const effOf = (day) => day.n_eff ? (day.peso_eff / day.n_eff) : NaN;
    // stato aperto/chiuso ricordato per chiave: il re-render non riapre più i rami chiusi
    const opened = (this._treeOpen = this._treeOpen || {});
    const op = (k) => (opened[k] === false ? "" : "open");
    box.innerHTML = Object.entries(tree).sort((a, b) => b[0].localeCompare(a[0])).map(([y, mesi]) => {
      const tot = Object.values(mesi).flat();
      const km = tot.reduce((a, r) => a + r.km, 0);
      return `<details class="anno" data-tk="${y}" ${op(y)}>
        <summary>▼ ${y} <span class="tr">${tot.length} giorni · <b>${this._i(km)} km</b></span></summary>
        ${Object.entries(mesi).sort((a, b) => b[0].localeCompare(a[0])).map(([m, rs]) => {
          const kmM = rs.reduce((a, r) => a + r.km, 0);
          const nm = NOMI_MESI[parseInt(m, 10) - 1] || m;
          return `<details class="mese" data-tk="${y}-${m}" ${op(`${y}-${m}`)}>
            <summary>▼ ${nm} <span class="tr">${rs.length} giorni · <b>${this._i(kmM)} km</b></span></summary>
            ${rs.map((r) => `<div class="giorno">• <b>${this._d(r.data)}</b> — ${this._fmt(r.km, 1)} km <span class="badge">${this._fmt(effOf(r), 1)}</span> · ${this._fmt(r.costo, 2)} €</div>`).join("")}
          </details>`;
        }).join("")}
      </details>`;
    }).join("");
    box.querySelectorAll("details[data-tk]").forEach((d) => {
      d.addEventListener("toggle", () => { this._treeOpen[d.dataset.tk] = d.open; });
    });
  }
  _tileStats(root) {
    const s = this._st(this._sid("statistiche_viaggi"));
    if (!s) return;
    const g = (keys) => {
      let v = this._attrAny(s, keys);
      if (v === null) {
        for (const p of ["ultimi_90_giorni", "ultimi_30_giorni", "ultimi_7_giorni"]) {
          const o = s.attributes[p];
          if (o) { const x = this._attrAny({ attributes: o }, keys); if (x !== null) { v = x; break; } }
        }
      }
      return v;
    };
    const set = (id, v, dec) => { const el = root.querySelector(`[data-t="${id}"]`); if (el) el.textContent = v; };
    set("tot_viaggi", this._i(parseFloat(g(["totale_viaggi", "n_trip", "viaggi"])) || 0));
    set("tot_km", this._i(parseFloat(g(["km_totali", "km"])) || 0));
    set("eff_media", this._fmt(parseFloat(g(["kwh_per_100km", "efficienza_media", "kwh_100km"])) || 0, 1));
    set("eff_best", this._fmt(parseFloat(g(["efficienza_best", "best", "record"])) || 0, 1));
    const min = parseFloat(g(["durata_totale_min", "tempo_guida"])) || 0;
    set("tempo", this._fmt(min / 60, 0) + " h");
    set("energia", this._i(parseFloat(g(["kwh_totali", "energia_usata", "kwh_totali_viaggi"])) || 0));
    const lr = this._st(this._sid("lista_ricariche"));
    set("n_ricariche", this._i(lr ? parseFloat(this._attrAny(lr, ["total"])) : null));
    set("energia_caricata", this._i(this._num(this._sid("energia_caricata_totale"))));
  }
  _drawSeasons(root) {
    // media kWh/100km per stagione dallo storico giornaliero (merged)
    const box = root.querySelector('[data-c="stagioni"]');
    if (!box) return;
    const hist = this._list(this._sid("storico_giornaliero"));
    const seasonOf = (m) => (m === 12 || m <= 2 ? "Inverno" : m <= 5 ? "Primavera" : m <= 8 ? "Estate" : "Autunno");
    const acc = { Inverno: { km: 0, kwh: 0 }, Primavera: { km: 0, kwh: 0 }, Estate: { km: 0, kwh: 0 }, Autunno: { km: 0, kwh: 0 } };
    hist.forEach((d) => {
      const m = parseInt(String(d.data || "").slice(5, 7), 10);
      if (!m) return;
      const km = parseFloat(d.km || 0) || 0;
      const kwh = parseFloat(d.kwh || 0) || 0;
      acc[seasonOf(m)].km += km;
      acc[seasonOf(m)].kwh += kwh;
    });
    const icons = { Inverno: "❄️", Primavera: "🌸", Estate: "☀️", Autunno: "🍂" };
    box.innerHTML = ["Inverno", "Primavera", "Estate", "Autunno"].map((s) => {
      const eff = acc[s].km > 0 ? acc[s].kwh / acc[s].km * 100 : NaN;
      return `<div class="row"><span>${icons[s]} ${s}</span><b>${isNaN(eff) ? "—" : this._fmt(eff, 1) + " kWh/100km"}</b></div>`;
    }).join("") || `<div style="color:var(--muted)">Nessun dato stagionale</div>`;
  }
  _rowsAttr(root) {
    // righe generiche: [data-attr="entityKey|attrKeys"] → testo
    root.querySelectorAll("[data-attr]").forEach((el) => {
      const [src, ...keys] = el.dataset.attr.split("|");
      let f = this._field(src);
      let s = typeof f === "string" ? this._st(f) : (f && f.entity_id ? f : null);
      if (!s) s = this._st(this._sid(src));
      let v = s ? this._attrAny(s, keys.length ? keys : [src]) : null;
      if (v === null) v = s ? s.state : "—";
      if (typeof v === "object") v = v.rotta ? `${v.rotta} · ${this._fmt(parseFloat(v.eff ?? 0), 1)} kWh/100km` : (v.value ?? v.testo ?? JSON.stringify(v));
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
  ["p4", "🔌", "Ricariche"], ["p11", "🎛️", "Wallbox"], ["p5", "💚", "Salute batteria"],
  ["p6", "🔧", "Manutenzione"], ["p7", "💰", "Risparmi"], ["p8", "⭐", "Extra"],
  ["p9", "🤖", "Automazioni"], ["p10", "⚙️", "Impostazioni"],
];
const THEMES = [
  ["blu", "#4d8dff", "🔵 Blu Megane"], ["giallo", "#F5CB39", "🟡 Giallo R5"],
  ["verde", "#57b98a", "🟢 Verde R4"], ["aviation", "#c9d4e2", "⚪ Grigio Aviation"],
];

const CSS = `
.app{background:var(--bg);color:var(--txt);font-family:'Segoe UI',system-ui,sans-serif;transition:background .25s,color .25s;user-select:text}
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
.sw{width:14px;height:14px;border-radius:4px;border:1px solid var(--line);display:inline-block}
h1{font-size:26px;margin-bottom:4px}
.sub{color:var(--muted);font-size:13.5px;margin-bottom:22px}
.page{display:none}.page.active{display:block}
.grid{display:grid;gap:16px}
.g3{grid-template-columns:repeat(3,1fr)}
.g2{grid-template-columns:repeat(2,1fr)}
@media(max-width:1100px){.g3{grid-template-columns:repeat(2,1fr)}}
@media(max-width:700px){.g3,.g2{grid-template-columns:1fr}.sidebar{display:none}.app{flex-direction:column;min-height:0}.main{margin-left:0;width:100%}}
.mobilenav{display:none;position:sticky;top:0;z-index:30;background:var(--panel2)}
  @media(max-width:700px){
    .card{overflow-x:auto}
    table{font-size:12px}
    th,td{padding:6px 6px}
  }
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
.card{position:relative;background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 1px 0 rgba(255,255,255,.05) inset,0 -14px 30px rgba(0,0,0,.42),0 16px 36px rgba(0,0,0,.32)}
.card::before{content:"";position:absolute;inset:0;border-radius:16px;padding:1px;background:linear-gradient(135deg,var(--accent),transparent 42%,rgba(255,255,255,.04));-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none}
.card h3{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:12px;font-weight:600}
.big{font-size:44px;font-weight:800;line-height:1}
.big small{font-size:18px;font-weight:600;color:var(--muted)}
.bar{height:10px;background:rgba(0,0,0,.35);border-radius:99px;margin-top:12px;overflow:hidden;box-shadow:inset 0 1px 3px rgba(0,0,0,.6)}
.bar i{display:block;height:100%;border-radius:99px;background:var(--accent);box-shadow:0 0 12px var(--accent)}
.row{display:flex;justify-content:space-between;font-size:14.5px;padding:8px 0;border-bottom:1px solid var(--line);gap:10px}
.row:last-child{border-bottom:none}
.row span:first-child{color:var(--muted)}
.clk{cursor:pointer}
.clk:hover{color:var(--accent)}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.chip{font-size:12px;padding:5px 11px;border-radius:999px;border:1px solid var(--line);background:var(--panel2)}
.chip.ok{color:var(--good);border-color:var(--good)}
.chip.acc{color:var(--accent);border-color:var(--accent)}
.dchip{cursor:pointer;user-select:none}
.dchip.on{background:var(--accent-soft);border-color:var(--accent);color:var(--accent)}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:16px}
@media(max-width:900px){.tiles{grid-template-columns:repeat(2,1fr)}}
.tile{position:relative;background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);border-radius:15px;padding:16px;display:flex;gap:13px;align-items:center;box-shadow:0 1px 0 rgba(255,255,255,.05) inset,0 -12px 26px rgba(0,0,0,.38),0 14px 30px rgba(0,0,0,.3)}
.tile .em{width:42px;height:42px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:21px;background:var(--accent-soft)}
.tile .v{font-size:24px;font-weight:800;line-height:1.05}
.tile .l{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-top:3px}
.cmd{position:relative;background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);border-radius:14px;padding:15px 8px;text-align:center;font-size:13.5px;cursor:pointer;box-shadow:0 1px 0 rgba(255,255,255,.05) inset,0 -10px 22px rgba(0,0,0,.35),0 12px 26px rgba(0,0,0,.3)}
.kv{text-align:center;background:rgba(255,255,255,.07);border:1px solid var(--line);border-radius:12px;padding:10px 4px;box-shadow:0 1px 0 rgba(255,255,255,.08) inset}
.kv:hover{border-color:var(--accent)}
.kv b{display:block;font-size:22px;font-weight:800;line-height:1.1}
.kv div{font-size:10.5px;letter-spacing:.04em;color:var(--muted);margin-top:2px}
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
.tree summary{cursor:pointer;list-style:none;user-select:none;display:flex;align-items:center;gap:8px}
.tree summary::-webkit-details-marker{display:none}
.tree .anno summary{font-weight:700}
.tree .mese summary{font-weight:600}
.tree .tr{margin-left:auto;color:var(--muted);font-weight:400;font-size:12px}
.tree .tr b{color:var(--txt)}
.totrow td{border-top:2px solid var(--accent);font-weight:700}
select,input{background:var(--panel2);color:var(--txt);border:1px solid var(--line);border-radius:8px;padding:8px 12px;font-size:14px}
.inp{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid var(--line);font-size:14px;gap:10px}
.inp input{width:110px;text-align:right}
.inp .u{color:var(--muted);font-size:12px;width:52px}
.btn{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);color:var(--txt);border-radius:11px;padding:11px 14px;font-size:13px;cursor:pointer;text-align:center;flex:1;box-shadow:0 1px 0 rgba(255,255,255,.05) inset,0 10px 22px rgba(0,0,0,.3)}
.btn:hover{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent-soft),0 1px 0 rgba(255,255,255,.05) inset,0 12px 24px rgba(0,0,0,.35)}
.btn.active{border-color:var(--accent);background:var(--accent-soft);color:var(--txt);font-weight:600;box-shadow:0 0 0 1px var(--accent)}
.palette .btn{flex:0 0 auto;min-width:150px;display:flex;align-items:center;gap:8px;justify-content:flex-start}
.netto{background:linear-gradient(135deg,var(--accent-soft),transparent);border-color:var(--accent)}
.carbox{position:relative;border-radius:14px;overflow:hidden;border:1px dashed var(--accent);background:radial-gradient(ellipse at 50% 115%,var(--accent-soft),transparent 60%),var(--panel);display:flex;align-items:center;justify-content:center;min-height:210px;flex-direction:column;gap:8px}
.carbox .ph{font-size:52px}
.carbox img{max-height:190px;max-width:90%;object-fit:contain}
.mapbox{border-radius:14px;overflow:hidden;border:1px solid var(--line);background:var(--panel2);height:260px}
.mapbox ha-map{display:block;width:100%;height:100%}
#toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(80px);background:var(--panel);color:var(--txt);border:1px solid var(--accent);border-radius:12px;padding:12px 20px;font-size:14px;opacity:0;transition:.3s;z-index:999}
#toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
`;

const PAGES = {
  p1: `<h1>Panoramica</h1>
  <div class="grid g3">
    <div class="card" style="padding:0;overflow:hidden">
      <div class="carbox" style="min-height:170px;border:none;border-radius:0;background:var(--panel);position:relative;padding:18px 16px">
        <div data-c="carimg" style="width:100%;display:flex;align-items:center;justify-content:center;min-height:120px"><div class="ph">🚗</div></div>
        <div style="position:absolute;top:10px;left:12px"><span class="chip" data-c="charging">🔓 Non in carica</span></div>
        <div style="position:absolute;top:10px;right:12px"><span class="chip acc">⚡ <span data-f="range">—</span> km</span></div>
      </div>
      <div style="padding:14px 16px">
        <div style="display:flex;align-items:center;gap:12px">
          <div style="font-size:42px;font-weight:800;color:var(--accent)"><span data-f="batt">—</span><span style="font-size:17px;color:var(--muted)">%</span></div>
          <div style="flex:1">
            <div class="bar" style="margin-top:0"><i data-b="battbar" style="width:0%"></i></div>
            <div style="display:flex;justify-content:space-between;gap:8px;font-size:13.5px;font-weight:600;margin-top:6px"><span>🔋 <span data-f="batt_kwh">—</span> kWh a bordo</span><span>🧭 <span data-f="odo">—</span> km</span></div>
            <div style="display:flex;justify-content:space-between;gap:8px;font-size:12px;color:var(--muted);margin-top:4px"><span>🔻 <span data-f="drain" data-dec="1">—</span>% consumata oggi</span><span>⚡ <span data-f="kwh_oggi_k" data-dec="2">—</span> kWh oggi</span></div>
          </div>
        </div>
        <div style="margin-top:10px;padding:8px 12px;border-radius:10px;background:var(--panel2);font-size:13px;display:flex;justify-content:space-between"><span data-c="chargestatus">Non in carica</span><b><span data-f="wb_potenza">—</span> kW</b></div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(72px,1fr));gap:8px;margin-top:12px">
          <div class="kv" data-more="km_per_kwh" style="cursor:pointer"><b data-f="km_per_kwh" data-dec="2">—</b><div>KM/KWH</div></div>
          <div class="kv" data-more="kwh_100" style="cursor:pointer"><b data-f="kwh_100" data-dec="2">—</b><div>KWH/100KM</div></div>
          <div class="kv" data-more="km_oggi" style="cursor:pointer"><b data-f="km_oggi" data-dec="1">—</b><div>KM OGGI</div></div>
          <div class="kv" data-more="drain" style="cursor:pointer"><b data-f="drain" data-dec="1">—</b><div>% OGGI</div></div>
          <div class="kv" data-more="kwh_oggi_k" style="cursor:pointer"><b data-f="kwh_oggi_k" data-dec="2">—</b><div>KWH OGGI</div></div>
        </div>
      </div>
    </div>
    <div class="card"><h3>Comandi Renault</h3>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
        <div class="cmd" data-more="charging"><span class="em">🔌</span>Carica<b data-v="cmd_charge">—</b></div>
        <div class="cmd" data-more="loc"><span class="em">📍</span>Zona ricarica<b data-v="cmd_zona">—</b></div>
        <div class="cmd" data-more="loc"><span class="em">🏠</span>Indirizzo<b data-v="cmd_addr">—</b></div>
        <div class="cmd" data-more="plug"><span class="em">🔗</span>Presa<b data-v="cmd_plug">—</b></div>
        <div class="cmd" data-cmd="ac"><span class="em">🧊</span>Avvia A/C<b>Premi ▸</b></div>
        <div class="cmd" data-cmd="charge"><span class="em">⚡</span>Avvia carica<b>Premi ▸</b></div>
        <div class="cmd" data-more="ora_compl"><span class="em">⏱</span>Fine ricarica<b data-v="cmd_ora">—</b></div>
        <div class="cmd" data-cmd="horn"><span class="em">📣</span>Clacson<b>Premi ▸</b></div>
        <div class="cmd" data-cmd="flash"><span class="em">💡</span>Lampeggia<b>Premi ▸</b></div>
      </div>
    </div>
    <div class="card"><h3>Efficienza</h3>
      <div class="grid g2" style="gap:10px">
        <div><div class="big" style="font-size:28px;color:var(--accent)" data-f="perc_100km" data-dec="1">—</div><div style="color:var(--muted);font-size:11px">% batteria/100km</div></div>
        <div><div class="big" style="font-size:28px" data-f="costo_km" data-dec="3">—</div><div style="color:var(--muted);font-size:11px">costo/km</div></div>
        <div><div class="big" style="font-size:28px" data-f="costo_100" data-dec="2">—</div><div style="color:var(--muted);font-size:11px">costo/100km</div></div>
      </div>
      <div style="margin-top:10px">
        <div class="row"><span>Viaggio in corso</span><b data-f="trip_attivo">—</b></div>
        <div class="row"><span>Carica programmata</span><b data-f="t_start_v">—</b></div>
        <div class="row"><span>⚡ Wallbox ora</span><b data-v="cmd_wb">—</b></div>
      </div>
    </div>
  </div>

  <div class="grid g2" style="margin-top:16px">
    <div class="card"><h3>📈 Km percorsi (7 giorni)</h3>
      <div id="kmchart" style="min-height:150px"></div>
    </div>
    <div class="card"><h3>🤖 Automazioni attive</h3>
      <div data-c="autos-on"></div>
    </div>
  </div>

  <div class="grid g3" style="margin-top:16px">
    <div class="card"><h3>Ultima ricarica</h3>
      <div class="row"><span>Data</span><b data-f="ultima_data">—</b></div>
      <div class="row"><span>Energia</span><b><span data-f="batt_ult">—</span> kWh</b></div>
      <div class="row"><span>Batteria</span><b data-f="batt_ult_pct">—</b></div>
      <div class="row"><span>Media</span><b><span data-f="media_ult">—</span> kW</b></div>
      <div class="row"><span>Costo · Eff.</span><b><span data-f="costo_corr">—</span> € · <span data-f="eff_ric">—</span>%</b></div>
    </div>
    <div class="mapbox" id="evmap"></div>
    <div class="card netto"><h3>💰 Risparmio netto</h3>
      <div class="row"><span>Carburante evitato</span><b style="color:var(--accent)"><span data-f="risp_tot">—</span> €</b></div>
      <div class="row"><span>+ Tagliandi</span><b><span data-f="risp_tagliandi">—</span> €</b></div>
      <div class="row"><span>+ Bollo</span><b><span data-f="risp_bollo">—</span> €</b></div>
      <div class="row" style="border-top:2px solid var(--accent)"><span><b>★ NETTO</b></span><b style="color:var(--accent);font-size:17px"><span data-f="risp_netto_tot" data-dec="2">—</span> €</b></div>
      <div style="text-align:center;margin-top:10px"><span class="chip acc">📄 dettaglio completo → Risparmi</span></div>
    </div>
  </div>

  <div class="card" style="margin-top:16px"><h3>Oggi a colpo d'occhio</h3>
    <div class="grid g2">
      <div>
        <div class="row"><span>🔴 Consumata oggi</span><b><span data-f="drain" data-dec="1">—</span>%</b></div>
        <div class="row"><span>🔋 kWh usati oggi</span><b><span data-f="kwh_oggi_k" data-dec="2">—</span> kWh</b></div>
        <div class="row"><span>🚗 Km oggi</span><b><span data-f="km_oggi">—</span> km</b></div>
      </div>
      <div>
        <div class="row"><span>⚡ Ricaricati oggi</span><b><span data-f="kwh_oggi_wb" data-dec="2">—</span> kWh · <span data-f="ricarica_oggi_pct" data-dec="0">—</span>%</b></div>
        <div class="row"><span>💰 Ricariche oggi</span><b><span data-f="costo_oggi" data-dec="2">—</span> €</b></div>
        <div class="row"><span>💰 Ricariche mensili</span><b><span data-f="costo_mese" data-dec="2">—</span> €</b></div>
      </div>
    </div>
  </div>`,

  p2: `<h1>Viaggi</h1>
  <div class="tiles">
    <div class="tile"><div class="em">🛣️</div><div><div class="v" data-f="stat_km_tot">—</div><div class="l">Distanza viaggi (km)</div></div></div>
    <div class="tile"><div class="em">📖</div><div><div class="v" data-f="stat_n_trip">—</div><div class="l">Viaggi totali</div></div></div>
    <div class="tile"><div class="em">⚡</div><div><div class="v" data-f="stat_eff">—</div><div class="l">Consumo medio kWh/100km</div></div></div>
  </div>
  <div class="card tree"><h3>Archivio</h3><div data-c="tree">—</div></div>
  <div class="card" style="margin-top:16px"><h3>Dettaglio viaggi recenti</h3>
    <div style="display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap">
      <select data-tf="year" style="width:auto"><option value="">Tutti gli anni</option></select>
      <select data-tfm="month" style="width:auto"><option value="">Tutti i mesi</option></select>
      <span style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)">da
        <input type="date" data-tfd="from" style="width:auto"></span>
      <span style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)">a
        <input type="date" data-tfd="to" style="width:auto"></span>
      <span class="chip" data-cmd="tfilter-reset" style="cursor:pointer">✖ azzera date</span>
    </div>
    <table><tr><th>Data</th><th>Ora</th><th>Km</th><th>SoC</th><th>Consumata</th><th>kWh</th><th>kWh/100km</th><th>Spesa</th><th>Partenza · via · paese</th><th>Arrivo · via · paese</th></tr>
    <tbody data-c="tab-viaggi"></tbody></table></div>`,

  p3: `<h1>Statistiche</h1>
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
      <div class="row"><span>⚡ Colonnine fuori casa</span><b data-attr="statistiche_viaggi|caricata_pubblica">—</b></div></div>
    <div class="card"><h3>Percorrenza</h3>
      <table><tr><th>Periodo</th><th>Usati</th><th>Caricati</th><th>KM</th></tr>
        <tr><td><b>OGGI</b></td><td data-per="oggi|usati">—</td><td data-per="oggi|caricati">—</td><td data-per="oggi|km">—</td></tr>
        <tr><td><b>IERI</b></td><td data-per="ieri|usati">—</td><td data-per="ieri|caricati">—</td><td data-per="ieri|km">—</td></tr>
        <tr><td><b>SETTIMANA</b></td><td data-per="settimana|usati">—</td><td data-per="settimana|caricati">—</td><td data-per="settimana|km">—</td></tr>
        <tr><td><b>MESE</b></td><td data-per="mese|usati">—</td><td data-per="mese|caricati">—</td><td data-per="mese|km">—</td></tr>
        <tr><td><b>ANNO</b></td><td data-per="anno|usati">—</td><td data-per="anno|caricati">—</td><td data-per="anno|km">—</td></tr></table></div></div>
  <div class="card" style="margin-top:16px"><h3>Rotte (consumo per zona)</h3>
    <div style="display:flex;gap:8px;margin-bottom:10px">
      <select data-rf="year" style="width:auto"><option value="">Tutti gli anni</option></select>
      <select data-rfm="month" style="width:auto"><option value="">Tutti i mesi</option></select>
    </div>
    <table><tr><th>Rotta</th><th>Viaggi</th><th>Km</th><th>kWh</th><th>kWh/100km</th><th>Spesa</th></tr>
    <tbody data-c="tab-rotte"></tbody></table></div>
  <div class="card" style="margin-top:16px"><h3>Storico mensile (tutti gli anni)</h3><div data-c="tab-mesi"></div></div>`,

  p4: `<h1>Ricariche</h1>
  <div class="tiles">
    <div class="tile" style="flex-direction:column;align-items:flex-start"><div class="l">OGGI</div><div class="v"><span data-f="kwh_oggi_wb" data-dec="2">—</span> kWh</div><div style="color:var(--muted);font-size:12px;margin-top:6px"><span data-f="costo_oggi">—</span> €</div></div>
    <div class="tile" style="flex-direction:column;align-items:flex-start"><div class="l">SETTIMANA</div><div class="v"><span data-f="kwh_sett_wb">—</span> kWh</div><div style="color:var(--muted);font-size:12px;margin-top:6px"><span data-f="costo_sett">—</span> €</div></div>
    <div class="tile" style="flex-direction:column;align-items:flex-start"><div class="l">MESE</div><div class="v"><span data-f="kwh_mese_wb">—</span> kWh</div><div style="color:var(--muted);font-size:12px;margin-top:6px"><span data-f="costo_mese">—</span> €</div></div>
    <div class="tile" style="flex-direction:column;align-items:flex-start"><div class="l">ANNO</div><div class="v"><span data-f="kwh_anno_wb">—</span> kWh</div><div style="color:var(--muted);font-size:12px;margin-top:6px"><span data-f="costo_anno">—</span> €</div></div></div>
  <div class="card"><h3>Filtri</h3>
    <div style="display:flex;gap:10px;flex-wrap:wrap">
      <select data-sel="sel_tipo"></select>
      <select data-sel="sel_periodo"></select>
      <select data-sel="sel_anno"></select></div></div>
  <div class="card"><h3>Storico ricariche</h3>
    <table><tr><th>Data</th><th>Tipo</th><th>Durata</th><th>Δ SoC</th><th>kWh</th><th>Ø kW</th><th>€/kWh</th><th>Costo</th></tr>
    <tbody data-c="tab-ricariche"></tbody></table></div>`,

  p5: `<h1>Salute batteria</h1>
  <div class="tiles">
    <div class="tile"><div class="em">📉</div><div><div class="v" data-f="cap_stim">—</div><div class="l">CAPACITÀ STIM. (kWh)</div></div></div>
    <div class="tile"><div class="em">🔋</div><div><div class="v" data-f="cap_nom">—</div><div class="l">NOMINALE (kWh)</div></div></div>
    <div class="tile"><div class="em">💚</div><div><div class="v" data-f="soh_est">—</div><div class="l">SOH STIMATO %</div></div></div>
    <div class="tile"><div class="em">✅</div><div><div class="v" data-f="soh_off">—</div><div class="l">SOH UFFICIALE %</div></div></div>
  </div>
  <div class="grid g3">
    <div class="card"><h3>SOH Ufficiale ✏️</h3>
      <div class="inp" style="border:none"><input data-n="n_soh" style="width:120px;font-size:26px;font-weight:800"><span class="u" style="font-size:16px">%</span></div>
      <div style="color:var(--muted);font-size:12px">modificabile, si salva nel number</div></div>
    <div class="card"><h3>SOH Stimato</h3><div class="big" style="font-size:34px;color:var(--accent)"><span data-f="soh_est">—</span><small>%</small></div>
      <div style="color:var(--muted);font-size:12px;margin-top:8px">dalle ricariche a casa</div></div>
    <div class="card"><h3>kWh per 1%</h3><div class="big" style="font-size:34px;color:var(--accent)"><span data-f="kwh_1pct">—</span> <small>kWh</small></div>
      <div style="color:var(--muted);font-size:12px;margin-top:8px">= capacità × SOH ÷ 100</div></div></div>
  <div class="grid g2" style="margin-top:16px">
    <div class="card"><h3>Dove finisce l'energia</h3>
      <div class="row"><span>Dalla rete (AC)</span><b><span data-f="rete_ult">—</span> kWh</b></div>
      <div class="row"><span>In batteria</span><b><span data-f="batt_ult">—</span> kWh</b></div>
      <div class="row"><span>Dispersa</span><b><span data-f="dispersa_ult">—</span> kWh</b></div>
      <div class="row"><span>Efficienza</span><b><span data-f="eff_ric">—</span>%</b></div></div>
    <div class="card"><h3>Sessioni analizzate</h3>
      <table><tr><th>Data</th><th>Δ SoC</th><th>Rete</th><th>Batteria</th><th>Eff.</th></tr>
      <tbody data-c="tab-salute"></tbody></table></div></div>`,

  p6: `<h1>Manutenzione</h1>
  <div class="grid g3">
    <div class="card"><h3>🔧 Tagliando</h3>
      <div class="row"><span>Prossimo (km)</span><b><span data-attr="tagliandi|prossimo_km">—</span> km</b></div>
      <div class="row"><span>Speso finora</span><b><span data-f="tagliandi">—</span> € (<span data-attr="tagliandi|n">—</span> interventi)</b></div>
      <div class="inp"><span>Scadenza a km</span><input type="number" data-mk="tagliando"><span class="u">km</span></div>
      <div class="inp"><span>Scadenza a data</span><input type="date" data-mk="tagliando" data-mdate="1"><span class="u"></span></div>
      <div class="btn" data-cmd="maint_tagliando" style="margin-top:8px">💾 Salva scadenza tagliando</div></div>
    <div class="card"><h3>🛞 Cambio gomme</h3>
      <div class="inp"><span>Scadenza a km</span><input type="number" data-mk="gomme"><span class="u">km</span></div>
      <div class="inp"><span>Scadenza a data</span><input type="date" data-mk="gomme" data-mdate="1"><span class="u"></span></div>
      <div class="btn" data-cmd="maint_gomme" style="margin-top:8px">💾 Salva scadenza gomme</div>
      <div style="color:var(--muted);font-size:11.5px;margin-top:8px">Le notifiche scadenze coprono tagliando e gomme.</div></div>
    <div class="card"><h3>🛡️ Assicurazione</h3>
      <div class="row"><span>Scadenza</span><b><span data-attr="assicurazione|data">—</span> · <span data-f="assic">—</span> gg</b></div>
      <div class="inp"><span>Costo annuo</span><input data-n="n_assic"><span class="u">€/anno</span></div>
      <div style="display:flex;gap:8px;margin-top:14px">
        <div class="btn" data-cmd="ass_plus6">Rinnova +6 mesi</div>
        <div class="btn" data-cmd="ass_plus12">Rinnova +1 anno</div></div></div></div>
  <div class="card" style="margin-top:16px"><h3>➕ Registra intervento</h3>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;align-items:center">
      <select data-ma="tipo" style="width:100%"><option>Tagliando</option><option>Cambio gomme</option><option>Riparazione</option><option>Altro</option></select>
      <input type="date" data-ma="data" style="width:100%">
      <input type="number" data-ma="km" placeholder="km" style="width:100%">
      <input type="number" data-ma="costo" step="0.01" placeholder="€" style="width:100%">
    </div>
    <div class="btn" data-cmd="maint_add" style="margin-top:10px">➕ Aggiungi intervento</div>
  </div>
  <div class="card" style="margin-top:16px"><h3>📋 Interventi registrati</h3>
    <table><tr><th>Data</th><th>Km</th><th>Tipo</th><th>€</th><th></th></tr>
    <tbody data-c="tab-tagliandi"></tbody></table></div>
  <div class="card netto" style="margin-top:16px"><h3>🏆 Risparmio manutenzione</h3>
    <div class="row"><span>Termica teorica (450 € × tagliandi)</span><b><span data-f="teo_tagliandi">—</span> €</b></div>
    <div class="row"><span>Spesa reale EV</span><b><span data-f="tagliandi">—</span> €</b></div>
    <div class="row"><span>Risparmio tagliandi</span><b style="color:var(--good)"><span data-f="risp_tagliandi">—</span> €</b></div>
    <div class="row"><span>Risparmio bollo</span><b><span data-f="risp_bollo">—</span> €</b></div></div>`,

  p7: `<h1>Risparmi</h1>
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
      <div style="color:var(--muted);font-size:12.5px;line-height:1.7">Carburante: km × consumo × prezzo − costi pagati.<br>Tagliandi: (km ÷ intervallo) × 450 € − spesa reale EV.<br>Bollo: imposta il bollo termico con <code>overrides.bollo_termico</code>. Il FV costa 0 €.</div></div></div>`,

  p8: `<h1>Extra</h1>
  <div class="grid g3">
    <div class="card"><h3>🔋 Vampire drain</h3><div class="big" style="font-size:32px;color:var(--accent)"><span data-f="vampire" data-dec="1">—</span><small>% oggi</small></div>
      <div style="color:var(--muted);font-size:12px;margin-top:6px">≈ <span data-attr="batteria_persa_da_fermo_oggi|equivalente_kwh">—</span> kWh oggi</div>
      <div style="color:var(--muted);font-size:12px;margin-top:4px">Mese ferma: <b><span data-attr="batteria_persa_da_fermo_mese|equivalente_kwh">—</span> kWh</b> (<span data-f="drain_mese_pct" data-dec="1">—</span>%)</div></div>
    <div class="card"><h3>🌍 CO2 evitata</h3><div class="big" style="font-size:32px;color:var(--good)"><span data-f="co2">—</span> <small>kg</small></div>
      <div style="color:var(--muted);font-size:12px;margin-top:6px">Anno: <span data-attr="co2_risparmiata|quest_anno">—</span> kg</div>
      <div style="color:var(--muted);font-size:11.5px;margin-top:4px">evitata = termica − rete</div></div>
    <div class="card"><h3>📅 Scadenze</h3>
      <table><tr><th>Tipo</th><th>Giorni</th></tr><tbody data-c="tab-scadenze"></tbody></table></div></div>
  <div class="grid g2" style="margin-top:16px">
    <div class="card"><h3>🌦️ Meteo vs consumi</h3>
      <div class="row"><span>Temperatura esterna</span><b><span data-f="temp_est">—</span> °C</b></div>
      <div class="row"><span>Consumo attuale</span><b><span data-f="kwh_100">—</span> kWh/100km</b></div>
      <div style="margin-top:12px;border-top:1px solid var(--line);padding-top:10px">
        <div style="color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">Media per stagione</div>
        <div data-c="stagioni"></div>
      </div></div>
    <div class="card"><h3>🏆 Top &amp; Stop · mese</h3>
      <div class="row"><span>Migliore</span><b><span data-topstop="migliore|kwh_per_100km">—</span> kWh/100km</b></div>
      <div class="row"><span>Peggiore</span><b><span data-topstop="peggiore|kwh_per_100km">—</span> kWh/100km</b></div>
      <div class="row"><span>Energia casa (totale)</span><b><span data-f="energia_casa">—</span> kWh</b></div></div>
  </div>
  <div class="card" style="margin-top:16px"><h3>ℹ️ Note</h3>
    <div style="color:var(--muted);font-size:12.5px;line-height:1.7">Vampire drain: % persa a fermo (batteria spenta).<br>CO2 evitata vs termica (termica − rete).<br>Scadenze: da <i>Prossima scadenza</i> (revisione/bollo/assicurazione).</div></div>`,

  p9: `<h1>Automazioni</h1>
  <div class="grid g2">
    <div class="card"><h3>Notifiche</h3>
      <div class="row"><span>📨 Servizio notify</span><b data-f="notify">—</b></div>
      <div style="color:var(--muted);font-size:11.5px;margin-top:6px">Avvio ricarica e promemoria batteria bassa si configurano in <b>Configura</b>.</div>
      <div style="margin-top:12px;border-top:1px solid var(--line);padding-top:10px">
        <div style="color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">🤖 Automazioni create — attiva/disattiva</div>
        <div data-c="autos-created" style="display:flex;flex-direction:column;gap:2px"></div>
        <div style="color:var(--muted);font-size:11.5px;margin-top:8px">Sono le automazioni create in Home Assistant (Impostazioni → Automazioni). Accendile/spegni da qui, senza YAML.</div>
      </div></div>
    <div class="card"><h3>⏰ Programma ricarica</h3>
      <div class="row"><span>Attivo</span><label class="switch"><input type="checkbox" data-schon="ricarica"><span></span></label></div>
      <div class="row"><span>Inizio</span><input type="time" data-sch="ricarica" data-k="inizio" value="23:30"></div>
      <div class="row"><span>Fine</span><input type="time" data-sch="ricarica" data-k="fine" value="07:00"></div>
      <div class="row"><span>SoC obiettivo %</span><input type="number" data-sch="ricarica" data-k="soc" value="80" min="50" max="100" style="width:80px"></div>
      <div class="row" style="flex-wrap:wrap;gap:6px"><span>Giorni</span>
        <span><span class="chip dchip" data-schday="ricarica|mon">Lun</span><span class="chip dchip" data-schday="ricarica|tue">Mar</span><span class="chip dchip" data-schday="ricarica|wed">Mer</span><span class="chip dchip" data-schday="ricarica|thu">Gio</span><span class="chip dchip" data-schday="ricarica|fri">Ven</span><span class="chip dchip" data-schday="ricarica|sat">Sab</span><span class="chip dchip" data-schday="ricarica|sun">Dom</span></span>
      </div>
      <div class="btn" data-cmd="schsave_ricarica" style="margin-top:10px">💾 Salva programma ricarica</div>
    </div>
    <div class="card"><h3>❄️ Programma clima</h3>
      <div class="row"><span>Attivo</span><label class="switch"><input type="checkbox" data-schon="clima"><span></span></label></div>
      <div class="row"><span>Orario</span><input type="time" data-sch="clima" data-k="inizio" value="07:00"></div>
      <div class="row" style="flex-wrap:wrap;gap:6px"><span>Giorni</span>
        <span><span class="chip dchip" data-schday="clima|mon">Lun</span><span class="chip dchip" data-schday="clima|tue">Mar</span><span class="chip dchip" data-schday="clima|wed">Mer</span><span class="chip dchip" data-schday="clima|thu">Gio</span><span class="chip dchip" data-schday="clima|fri">Ven</span><span class="chip dchip" data-schday="clima|sat">Sab</span><span class="chip dchip" data-schday="clima|sun">Dom</span></span>
      </div>
      <div class="btn" data-cmd="schsave_clima" style="margin-top:10px">💾 Salva programma clima</div>
      <div style="color:var(--muted);font-size:11px;margin-top:6px">Premе il tasto Avvia A/C all'orario scelto (modo/temperatura non sono inviabili coi button Renault).</div>
    </div>
    <div class="card"><h3>🔔 Avviso batteria bassa</h3>
      <div class="row"><span>Attivo</span><label class="switch"><input type="checkbox" data-sw="sw_low"><span></span></label></div>
      <div class="row"><span>Soglia</span><input type="number" data-n="n_low_soc" min="5" max="80" step="1" style="width:80px"><span class="u">%</span></div>
      <div class="row"><span>Dalle</span><input type="time" data-time="t_low_start"></div>
      <div class="row"><span>Alle</span><input type="time" data-time="t_low_end"></div>
      <div class="row" style="flex-wrap:wrap;gap:6px"><span>Giorni</span>
        <span><span class="chip dchip" data-lowday="mon">Lun</span><span class="chip dchip" data-lowday="tue">Mar</span><span class="chip dchip" data-lowday="wed">Mer</span><span class="chip dchip" data-lowday="thu">Gio</span><span class="chip dchip" data-lowday="fri">Ven</span><span class="chip dchip" data-lowday="sat">Sab</span><span class="chip dchip" data-lowday="sun">Dom</span></span>
      </div>
      <div class="btn" data-cmd="lowsave" style="margin-top:10px">💾 Salva giorni</div>
      <div style="color:var(--muted);font-size:11.5px;margin-top:6px">Una notifica al giorno quando l'auto è <b>a casa</b>, sotto la soglia, nella fascia oraria e nei giorni scelti.</div>
    </div>
  </div>
  <div style="color:var(--muted);font-size:11.5px;margin-top:8px">La schedulazione crea/aggiorna un'<b>automazione</b> in Home Assistant (orario + giorni) che preme il tasto di avvio.</div>
  <div class="card" style="margin-top:16px"><h3>Come si cambiano i parametri</h3>
    <div style="color:var(--muted);font-size:13px;line-height:1.8">
      Tutto in <b>Impostazioni → Integrazioni → Renault EV Center → Configura</b>:
      servizio notify, % minima e fascia oraria del promemoria, modalità programmazione
      (orario o %), orari e % di avvio/stop, pulsante di avvio carica e number target
      per lo stop. Gli interruttori si trovano anche tra i dispositivi
      ("Renault EV Center" → switch).</div></div>`,

  p10: `<h1>Impostazioni</h1>
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
      <div class="inp"><span>Costo assicurazione</span><input data-n="n_assic"><span class="u">€/anno</span></div></div>
    <div class="card"><h3>Reset &amp; export</h3>
      <div style="display:flex;flex-direction:column;gap:8px">
        <div class="btn" data-cmd="close_trip">🏁 Chiudi viaggio ora</div>
        <div class="btn" data-cmd="reset_km">🔄 Reset contatori Km</div>
        <div class="btn" data-cmd="reset_energia">🔄 Reset contatori Energia</div>
        <div class="btn" data-cmd="reset_costi">🔄 Reset contatori Costi</div>
        <div class="btn" data-cmd="csv">📥 Esporta viaggi CSV</div></div></div></div>
  <div class="card palette" style="margin-top:16px"><h3>🎨 Palette (colori Renault)</h3>
    <div style="display:flex;gap:8px;flex-wrap:wrap">${THEMES.map(([id, dot, label]) => `<button class="btn" data-palette="${id}"><span class="sw" style="background:${dot}"></span> ${label}</button>`).join("")}</div>
    <div style="color:var(--muted);font-size:11.5px;margin-top:10px">Temi HA equivalenti in /themes: renault-blu, renault-giallo, renault-verde, renault-aviation</div></div>
  <div class="card" style="margin-top:16px"><h3>🔔 Notifiche</h3>
    <div class="inp"><span>Servizio notify (es. notify.michele)</span><input data-ls="rec_notify" data-f="notify" style="width:170px"><span class="u"></span></div>
    <div class="inp"><span>Giorni preavviso scadenze</span><input data-ls="rec_preavviso" value="30"><span class="u">gg</span></div></div>
  <div class="card" style="margin-top:16px"><h3>🤖 Automazioni</h3>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <div class="btn" data-cmd="create_automations">✨ Crea automazioni consigliate</div></div>
    <div class="note">Crea in Home Assistant 3 automazioni pronte: <b>ricarica completata</b> (kWh, SoC, costo),
      <b>batteria bassa fuori casa</b>, <b>riassunto giornaliero</b> alle 21:30. Sono modificabili da
      Impostazioni → Automazioni. Notifiche via persistent_notification se nessun servizio notify configurato.</div></div>`,

  p11: `<h1>Wallbox</h1>
  <div class="grid g2">
    <div class="card"><h3>🔌 Stato wallbox</h3>
      <div class="big" style="font-size:32px;color:var(--accent)"><span data-wb="state">—</span></div>
      <div class="row"><span>Potenza ora</span><b><span data-wb="power">—</span></b></div>
      <div class="row"><span>Corrente</span><b><span data-wb="current">—</span></b></div>
      <div class="row"><span>Tensione</span><b><span data-wb="voltage">—</span></b></div>
      <div class="row"><span>Temperatura</span><b><span data-wb="temp">—</span></b></div>
      <div class="row"><span>Motivo limite</span><b><span data-wb="limit">—</span></b></div></div>
    <div class="card"><h3>⏱️ Sessione corrente</h3>
      <div class="big" style="font-size:32px;color:var(--good)"><span data-wb="session_kwh">—</span></div>
      <div class="row"><span>Tempo di ricarica</span><b><span data-wb="session_time">—</span></b></div>
      <div class="row"><span>Energia totale erogata</span><b><span data-wb="total_kwh">—</span></b></div>
      <div style="display:flex;gap:8px;margin-top:14px">
        <div class="btn" data-cmd="wb_start">▶️ Avvia</div>
        <div class="btn" data-cmd="wb_stop">⏹️ Ferma</div></div></div></div>
  <div class="grid g2" style="margin-top:16px">
    <div class="card"><h3>🎚️ Corrente di carica (A)</h3>
      <div class="inp"><span>Limite</span><input id="wb_amp" type="range" min="6" max="32" step="1" style="flex:1" oninput="this.closest('.inp').querySelector('#wb_amp_live').textContent=this.value+' A'"><b id="wb_amp_live" style="min-width:54px;text-align:right">—</b></div>
      <div style="color:var(--muted);font-size:11.5px;margin-top:4px" id="wb_amp_val">—</div>
      <div class="btn" data-cmd="wb_set_current" style="margin-top:10px">💾 Applica corrente</div>
      <div class="note">Imposta il limite della wallbox (<code>number</code>). Le automazioni di bilanciamento possono sovrascriverlo.</div></div>
    <div class="card"><h3>☀️ Bilanciamento solare</h3>
      <div class="btn" data-cmd="wb_bal_toggle" style="margin-bottom:6px">☀️ Bilanciamento solare: —</div>
      <div class="row"><span>Surplus rete</span><b><span data-wb="bal_surplus">—</span> W</b></div>
      <div class="row"><span>Prelievo rete</span><b><span data-wb="bal_grid">—</span> W</b></div>
      <div class="row"><span>Ampere impostati</span><b><span data-wb="bal_amps">—</span> A</b></div>
      <div class="row"><span>Ultimo aggiustamento</span><b><span data-wb="bal_ts">—</span></b></div>
      <div class="note">Adatta gli ampere per tenere il prelievo da rete ~0. Sensori rete/batteria e W per A in <b>Configura → Bilanciamento</b>.</div></div></div>
  <div class="card" style="margin-top:16px"><h3>🏠 Bilanciamento casalingo</h3>
    <div class="note">Se la wallbox non fa da sé il bilanciamento domestico (non superare il contatore di casa), usa automazioni Home Assistant — es. quelle che riducono gli ampere quando il consumo sale. Trovo per nome:</div>
    <div data-c="wb-home-autos" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px"></div></div>`,
};

if (!customElements.get("renault-ev-center-panel")) {
  customElements.define("renault-ev-center-panel", RenaultEvCenterPanel);
}


