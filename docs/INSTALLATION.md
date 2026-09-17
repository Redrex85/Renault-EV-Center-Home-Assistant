# Installation guide — Renault EV Center

From install to a fully working dashboard in **~10 minutes**.

## Prerequisites

- Home Assistant **2025.11+**
- The official **Renault integration** configured with your vehicle
- *(Optional)* A wallbox integrated into HA (Wallbox, go-e, Easee, OCPP, Shelly EM…)

## 1. Install

**HACS:** HACS → ⋮ → Custom repositories → add `https://github.com/Redrex85/Renault-EV-Center-Home-Assistant` (category: Integration) → download → restart HA.

**Manual:** copy `custom_components/renault_ev_center/` into `<config>/custom_components/`, restart HA.

## 2. Configure

Settings → Devices & Services → Add Integration → **Renault EV Center**:

### Step 1 — Car
Pick a short lowercase name (`Megane`) — it becomes the entity prefix — then select:
odometer (`sensor.mileage`), battery level (`sensor.battery_level`), range (`sensor.battery_autonomy`),
charging (`binary_sensor.charging` or `sensor.charge_state`), optional plug status and GPS tracker.

### Step 2 — Wallbox
Enable the toggle and map: instant power (W or kW, auto-converted), charger state, session energy counter and/or total energy counter.

No wallbox? Leave everything off — public charges can be logged manually via the `add_manual_charge` service.

### Step 3 — Settings
Battery capacity (60 kWh for Megane EV60), target SoC, home/public/solar prices per kWh,
solar zone name, poll interval, trip timeout, optional fuel comparison.

Everything can be changed later from the integration's Configure dialog.

## 3. Dashboards

With "Create dashboard" enabled, the sidebar panel is created automatically (11 views + the custom 3D panel).
To set it up manually, import the YAML files from [`dashboards/`](../dashboards/).
If your car isn't named `Megane`, find & replace the `sensor.megane_` prefix.

## 4. Services

```yaml
renault_ev_center.close_trip            # force-close the active trip
renault_ev_center.reset_counters        # scope: km | energia | costi | viaggi | ricariche | all
renault_ev_center.add_manual_charge     # kwh, costo, tipo
renault_ev_center.export_trips_csv      # writes CSVs to config/renault_ev_center_export/
renault_ev_center.create_dashboard      # (re)create the sidebar dashboard
renault_ev_center.create_automations    # create the 3 recommended automations
renault_ev_center.add_maintenance       # data, km, costo, tipo, note
renault_ev_center.renew_insurance       # mesi (6|12) or data
renault_ev_center.set_scadenza          # nome, data
renault_ev_center.set_tagliando         # mode (km|data), valore
```

## 4.1 Privacy and addresses (geocoding)

On the **Trips** page the integration can show the **street and country** of departure/arrival,
derived from the GPS coordinates via **OpenStreetMap (Nominatim)**.

- **On by default.** To **turn it off** (no external calls, no addresses):
  *Settings → Devices & Services → Renault EV Center → **Configure** → Settings → "Street and
  country in trips"* (clear the checkbox).
- Coordinates are **rounded** and cached locally: geocoding runs once per location and only when
  a trip closes.
- **"Average speed estimate for trip departure time"** (default 30 km/h): used only to estimate
  the departure time when the car has been parked for a long time (the Renault cloud updates
  odometer/GPS on ignition off). Raise it if your trips are faster.

## 5. Troubleshooting

| Issue | Fix |
|---|---|
| Not showing in HACS | Added with category "Integration"? Restarted HA? |
| Entities unavailable | Renault cloud updates slowly; wait or reload the Renault integration |
| Daily km stays 0 | Wrong odometer entity selected |
| Costs stay 0 | Set prices; without wallbox use manual charges |
| Trips never close | Lower the trip timeout option |
| Dashboard "entity not found" | Replace the `sensor.megane_` prefix |

Data lives in `<config>/.storage/renault_ev_center.<entry_id>` — include `.storage` in backups.
