/**
 * Renault EV Center Card
 * ======================
 * Card Lovelace dedicata: auto con barra batteria, stato carica,
 * efficienza, viaggio in corso e wallbox — in un solo blocco.
 *
 * Installazione:
 *   1) copia questo file in /config/www/renault-ev-center/
 *   2) Impostazioni → Dashboard → ⋮ → Risorse → + → URL:
 *      /local/renault-ev-center/renault-ev-center-card.js
 *   3) aggiungi la card manuale di tipo "custom:renault-ev-center-card"
 *
 * Configurazione:
 *   type: custom:renault-ev-center-card
 *   name: Renault            # prefisso entità (il nome dell'auto)
 *   image: /local/renault-ev-center/auto.png
 *   battery_entity: sensor.battery_level
 *   range_entity: sensor.battery_autonomy
 *   odometer_entity: sensor.mileage
 */
class RenaultEvCenterCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.name) {
      throw new Error("renault-ev-center-card: serve il campo 'name' (prefisso entità)");
    }
    this._config = Object.assign(
      {
        name: "Renault",
        image: "/local/renault-ev-center/auto.png",
        battery_entity: "sensor.battery_level",
        range_entity: "sensor.battery_autonomy",
        odometer_entity: "sensor.mileage",
      },
      config
    );
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  get _p() {
    return String(this._config.name).toLowerCase();
  }

  _st(id) {
    if (!this._hass) return "0";
    const s = this._hass.states[id];
    return s ? s.state : "0";
  }

  _attr(id, name) {
    if (!this._hass) return null;
    const s = this._hass.states[id];
    return s ? s.attributes[name] : null;
  }

  _render() {
    const c = this._config;
    const p = this._p;
    const batt = parseFloat(this._st(c.battery_entity)) || 0;
    const range = parseFloat(this._st(c.range_entity)) || 0;
    const odo = parseFloat(this._st(c.odometer_entity)) || 0;
    const inCarica = this._st(`binary_sensor.${p}_in_carica`) === "on";
    const kmPerKwh = this._st(`sensor.${p}_km_per_kwh`);
    const kwh100 = this._st(`sensor.${p}_kwh_per_100km`);
    const kmOggi = this._st(`sensor.${p}_km_giornalieri`);
    const costoKm = this._st(`sensor.${p}_costo_per_km`);
    const tipo = this._st(`sensor.${p}_tipo_ricarica_attuale`);
    const wbKw = this._st(`sensor.${p}_wallbox_potenza`);
    const tripOn = this._st(`sensor.${p}_trip_attivo`) === "on";
    const tripKm = this._st(`sensor.${p}_km_trip_corrente`);
    const battKwh = this._st(`sensor.${p}_batteria_kwh_disponibili`);
    const scaricaOggi = this._st(`sensor.${p}_batteria_scaricata_oggi`);
    const usatiOggi = this._st(`sensor.${p}_energia_batteria_giornaliera`);

    const barColor =
      batt < 25 ? "#ff5252" : batt < 50 ? "#ff9f43" : batt < 80 ? "#4caf50" : "#2e7d32";
    const accent = getComputedStyle(document.body).getPropertyValue("--primary-color") || "#4d8dff";

    const chip = (txt, color) =>
      `<span style="font-size:12px;padding:4px 10px;border-radius:999px;border:1px solid ${color}33;background:${color}1a;color:${color};font-weight:600">${txt}</span>`;

    this.shadowRoot.innerHTML = `
      <ha-card style="border-radius:16px;padding:18px;background:var(--card-background-color,var(--ha-card-background));border:1px solid var(--divider-color)">
        <div style="position:relative;text-align:center">
          <img src="${c.image}" alt="auto"
               style="max-width:100%;max-height:190px;border-radius:12px"
               onerror="this.style.display='none'"/>
          <div style="position:absolute;top:6px;left:10px">${chip(inCarica ? "⚡ In carica" : "🔌 Non in carica", inCarica ? "#4caf50" : "#9e9e9e")}</div>
          <div style="position:absolute;top:6px;right:10px">${chip(`⚡ ${range} km`, accent.trim() || "#4d8dff")}</div>
        </div>

        <div style="display:flex;align-items:center;gap:14px;margin-top:12px">
          <div style="font-size:40px;font-weight:800;color:${barColor}">${batt}<span style="font-size:17px;color:var(--secondary-text-color)">%</span></div>
          <div style="flex:1">
            <div style="height:10px;background:var(--divider-color);border-radius:6px;overflow:hidden">
              <div style="height:100%;width:${Math.max(batt, 1)}%;background:${barColor};border-radius:6px;transition:width .4s"></div>
            </div>
            <div style="display:flex;justify-content:space-between;gap:8px;font-size:13.5px;font-weight:600;margin-top:6px">
              <span>🔋 ${battKwh} kWh a bordo</span><span>🧭 ${odo} km</span>
            </div>
            <div style="display:flex;justify-content:space-between;gap:8px;font-size:12px;color:var(--secondary-text-color);margin-top:4px">
              <span>🔻 ${scaricaOggi}% consumata oggi</span><span>⚡ ${usatiOggi} kWh oggi</span>
            </div>
          </div>
        </div>

        ${inCarica ? `
        <div style="margin-top:10px;padding:9px 12px;border-radius:10px;background:${accent}14;font-size:13.5px;display:flex;justify-content:space-between">
          <span>${tipo}</span><b>${wbKw} kW</b>
        </div>` : `
        <div style="margin-top:10px;padding:9px 12px;border-radius:10px;background:var(--secondary-background-color);font-size:13.5px;display:flex;justify-content:space-between">
          <span>${tipo}</span><span>${tripOn ? `🚗 viaggio in corso · <b>${tripKm} km</b>` : "—"}
        </span></div>`}

        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:12px">
          ${[
            ["km/kWh", kmPerKwh],
            ["kWh/100km", kwh100],
            ["Km oggi", kmOggi],
            ["€/km", costoKm],
          ]
            .map(
              ([l, v]) => `<div style="text-align:center;background:var(--secondary-background-color);border-radius:10px;padding:9px 4px">
                <div style="font-size:17px;font-weight:800">${v}</div>
                <div style="font-size:10.5px;color:var(--secondary-text-color);text-transform:uppercase;letter-spacing:.05em">${l}</div>
              </div>`
            )
            .join("")}
        </div>

        ${tripOn ? `<div style="margin-top:10px;font-size:13px;color:var(--secondary-text-color)">🏁 Viaggio in corso: <b>${tripKm} km</b> — si chiuderà ~20 min dopo lo spegnimento</div>` : ""}
      </ha-card>
    `;
  }

  getCardSize() {
    return 5;
  }

  static getStubConfig() {
    return { name: "Renault", image: "/local/renault-ev-center/auto.png" };
  }
}

customElements.define("renault-ev-center-card", RenaultEvCenterCard);

try {
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "renault-ev-center-card",
    name: "Renault EV Center Card",
    description: "Auto, batteria, carica ed efficienza Renault in un solo blocco",
    preview: true,
  });
} catch (e) {
  /* ambiente non-HA (demo): ignora */
}

console.info("%c RENAULT EV CENTER CARD %c v1.0.3.5 ", "background:#4d8dff;color:#fff", "background:#333;color:#fff");
