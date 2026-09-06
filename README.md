<p align="center">
  <img src="docs/images/logo_renault.png" alt="Renault" width="260">
</p>

# Renault EV Center

<p align="left">
  <a href="https://www.paypal.me/TUO-NOME"><img src="https://img.shields.io/badge/Dona-PayPal-00457C?logo=paypal" alt="PayPal"></a>
  <a href="https://www.buymeacoffee.com/TUO-NOME"><img src="https://img.shields.io/badge/Offrimi%20un%20caffè-BuyMeACoffee-FFDD00?logo=buy-me-a-coffee" alt="BuyMeACoffee"></a>
  <a href="https://github.com/Redrex/renault-ev-center/releases"><img src="https://img.shields.io/github/v/release/Redrex/renault-ev-center" alt="Release"></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2025.11%2B-41BDF5?logo=homeassistant" alt="HA">
</p>
<!-- Sostituisci TUO-NOME con i tuoi link reali PayPal.me e buymeacoffee.com/username -->

**Viaggi, consumi, costi e ricariche per le tue Renault elettriche — direttamente in Home Assistant.**

Un *companion* stile **TeslaMate/LeapMotor Mate** per **Megane E-Tech, Scenic E-Tech, Zoe, Twingo E-Tech e Alpine A290**, costruito sopra l'integrazione **Renault ufficiale di Home Assistant**: nessun account extra, nessun cloud, nessuna riga di codice. Installi da HACS, scegli le entità dalla lista, e via.

> 🇬🇧 [English below](#-english)

---

## ✨ Cos'è

L'integrazione **Renault** ti dà i numeri grezzi (% batteria, autonomia, odometro). **Renault EV Center** li trasforma in quello che manca:

| | |
|---|---|
| 🛣️ **Viaggi automatici** | Rileva ogni spostamento dall'odometro, calcola km, batteria consumata, kWh ed efficienza (kWh/100km), chiude il viaggio da solo dopo la sosta, con **costo stimato** e **fonte dell'ultima ricarica** prima della partenza |
| ⚡ **Ricariche** | Sessioni con energia wallbox (AC) misurata, SoC iniziale→finale, durata, tipo (Casa/Fotovoltaico/Pubblica) e costo reale |
| 🔎 **Lista ricariche filtrabile** | Filtri per tipo e periodo (settimana/mese/anno/tutto) con **somma automatica** di kWh e € |
| 💰 **Costi veri** | €/km, €/100km, costo ricariche giorno/settimana/mese/anno/totale, prezzi separati per casa/colonnina/fotovoltaico modificabili **dalla dashboard** |
| 📊 **Statistiche e report** | Contatori con `last_period` (come utility_meter), tabelle **Generale/Settimanale/Mensile**, storico 365 giorni, report mensile |
| 🔋 **Stime ricarica** | Tempo residuo, ora di completamento prevista, energia mancante e costo stimato verso il tuo % obiettivo |
| 🌿 **Risparmio vs termica** | Quanti euro hai risparmiato rispetto alla tua vecchia diesel/benzina (totale, mese, anno) |
| 💚 **Salute batteria** | Efficienza di ricarica (mai >100%), **energia dispersa**, breakdown rete/batteria, SOH stimato dalle ricariche e **SOH ufficiale** della concessionaria, kWh per 1% |
| 🔧 **Manutenzione** | Registro tagliandi con spesa reale, prossimo tagliando **a scelta per km o data**, **assicurazione** con rinnovo +6 mesi/+1 anno/data e costo annuo |
| 🤖 **Automazioni integrate** | Notifica avvio/fine ricarica (con kWh, SoC e costo), **promemoria batteria bassa** a casa (% e fascia oraria), **carica programmata** via wallbox (per orario **o** percentuale) — tutto on/off e regolabile dalla vista Automazioni |
| 🖼️ **Installazione guidata** | Scelta del **modello** (imposta la foto dell'auto) e **dashboard creata automaticamente** nella barra laterale con tutte le 10+ viste già configurate |
| 📱 **Vista Mobile** | Pagina compatta pensata per il telefono; tutte le altre viste si adattano comunque allo schermo |
| 🛣️ **Viaggi verificati** | Doppia verifica all'arrivo: chiusura immediata se colleghi la carica + **coordinate GPS reali** salvate per ogni viaggio |

Tutto è calcolato **localmente nel tuo Home Assistant** e salvato in `.storage` (persistente tra riavvii). Niente pyscript, niente package YAML, niente utility_meter da configurare a mano.

## 🖼️ Anteprima

Apri **[`preview/index.html`](preview/index.html)** nel browser per vedere come appariranno le dashboard (dati fittizi).

| Panoramica | Viaggi | Statistiche | Ricariche |
|---|---|---|---|
| Batteria, autonomia, carica live, ultima ricarica, viaggi recenti | Riepilogo periodi, grafici giornalieri, tabella dettagliata | Mese/anno, trend 30gg e 12 mesi, report mensile, risparmi | Wallbox, energie caricate, spese, storico sessioni |

*(Screenshot reali in arrivo — PR benvenute!)*

## 📦 Requisiti

1. Home Assistant **2025.11+** (le dashboard usano la card nativa *metric*)
2. L'integrazione **[Renault](https://www.home-assistant.io/integrations/renault/)** configurata (con il veicolo collegato)
3. *(Opzionale)* Una wallbox integrata in HA: Wallbox, go-e, Easee, Zappi, OCPP, Shelly EM dedicato…

> Funziona anche senza wallbox: le ricariche pubbliche vengono stimate dal delta SoC e puoi registrarle a mano col servizio `add_manual_charge`.

## 🔧 Installazione

### Via HACS (consigliato)

1. **HACS** → ⋮ → **Repository personalizzati**
2. Incolla `https://github.com/Redrex/renault-ev-center`
3. Categoria: **Integrazione** → Aggiungi
4. Apri **Renault EV Center** → Scarica
5. **Riavvia Home Assistant**
6. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → "Renault EV Center"**

### Manuale

Copia la cartella `custom_components/renault_ev_center/` dentro `<config>/custom_components/`, riavvia e aggiungi l'integrazione dal menu.

## 🧙 Configurazione (3 schermate)

### 1️⃣ L'auto

Dai un nome breve all'auto (es. `Renault`) — diventa il prefisso di tutte le entità create (`sensor.renault_…`). Poi seleziona:

| Campo | Entità tipica dell'integrazione Renault |
|---|---|
| Modello | Megane E-Tech, Scenic E-Tech, Zoe, Twingo, A290 → imposta la **foto dell'auto** |
| Crea dashboard | Crea da sola la plancia laterale con tutte le viste |
| Odometro | `sensor.mileage` |
| Batteria (%) | `sensor.battery_level` |
| Autonomia | `sensor.battery_autonomy` |
| In carica | `binary_sensor.charging` oppure `sensor.charge_state` |
| Spina (opz.) | `sensor.plug_state` |
| GPS (opz.) | `device_tracker.location` |

### 2️⃣ La wallbox

Attiva l'interruttore se hai una wallbox in HA e mappa i sensori:

| Campo | Esempi |
|---|---|
| Potenza istantanea | `sensor.wallbox_instant_power` (W o kW — conversione automatica) |
| Stato wallbox | `sensor.wallbox_charger_state` (cerca lo stato tipo *charging*) |
| Contatore energia sessione | kWh della sessione corrente |
| Contatore energia totale | kWh totali erogati (usato se manca quello di sessione) |
| Avvio/stop carica (per l'automazione) | switch o button della wallbox |
| Target di carica (fallback stop) | `number.*charge_target` Renault |

### 3️⃣ Impostazioni

Capacità batteria (**60 kWh** per Megane EV60, 40 per EV40), % obiettivo ricarica, prezzi **casa/colonnina/fotovoltaico**, nome della zona FV (es. `beb`), intervallo aggiornamento, minuti di timeout viaggi, e opzionale confronto con auto termica (consumo e prezzo del gasolio/benzina).

Tutto è modificabile dopo: ⚙️ **Integrazioni → Renault EV Center → Configura**.

## 📈 Cosa crea

Oltre **40 entità** sul dispositivo *"Renault EV Center"* (prefisso = nome scelto):

```
Sensori      Km G/S/M/A (+last_period) · Energia Caricata G/S/M/A/Tot · Costo Ricarica G/S/M/A/Tot
             Km per kWh · kWh/100km · Costo/km · Costo/100km · kWh Totali · %/100km
             Batteria kWh · % Caricata/Scaricata Oggi · Energia Batteria (periodi)
             Tempo/Completamento/Costo Ricarica · Tipo Ricarica · Ultima Ricarica · Ricariche
             Trip Attivo · Km/Durata Trip · Ultimo Trip (con GPS e verifica) · Viaggi Oggi
             Statistiche Viaggi (7/30/90/totale) · Archivio · Percorrenza · Report Generale
             Efficienza Ricarica · Perdite · Energia Batteria Ultima Ricarica · kWh per 1%
             SOH Stimato · Risparmi (termica/tagliandi/bollo/netto) · CO2 · Tagliandi
             Vampire Drain · Consumo per Zona · Scadenze · Viaggio Top/Stop · FV Mese
Binary       In Carica · Wallbox in Carica
Switch       Notifica Avvio/Fine Ricarica · Promemoria Batteria Bassa · Carica Programmata
Number       Costo Casa/Colonnina/FV · Capacità · Obiettivo Ricarica · SOH Ufficiale
             Costo Assicurazione · % Promemoria · % Avvio/Stop Carica
Time         Promemoria Inizio/Fine · Carica Orario Avvio/Stop
Select       Filtro Tipo/Periodo/Anno Ricariche
Pulsanti     Chiudi Viaggio · Esporta CSV · Reset Km/Energia/Costi
```

## 🎛️ Dashboard incluse (create automaticamente)

Alla configurazione viene creata **da sola** la dashboard laterale con tutte le viste
(opzione disattivabile; servizio `renault_ev_center.create_dashboard` per ricrearla):

| Vista | Contenuto |
|---|---|
| Panoramica | Foto auto, batteria, efficienza, comandi Renault, mappa, box Risparmi |
| Viaggi | Albero Anno→Mese→Giorno stile LeapMotor + dettaglio con spesa e verifica GPS |
| Statistiche | Tile totali, percorrenza, ricariche differenziate, anno→mese + grafici |
| Ricariche | Filtri tipo/periodo/**anno**, lista stile app (Δ%, ØkW), tabelle G/S/M |
| Salute batteria | SOH ufficiale (inline) e stimato, rete/batteria/dispersa |
| Manutenzione | Tagliandi (km o data) + Assicurazione (rinnovi, costo) |
| Risparmi | Carburante, tagliandi (termica 450 € − reale), bollo, netto, FV |
| Extra | Vampire drain, rotte, meteo, CO₂, scadenze, top&stop, Energy Dashboard |
| Automazioni | Interruttori + % e orari delle automazioni integrate |
| Impostazioni | Prezzi, batteria, reset, export |
| Mobile | Vista compatta per il telefono |

Card custom opzionali (HACS → Frontend): **bar-card**, **apexcharts-card**, **mini-graph-card**.
Foto dell'auto: scelta dal modello nel wizard o personale in `/config/www/renault-ev-center/auto.png`.

> Se la tua auto non si chiama "Renault", sostituisci `sensor.renault_` con il prefisso giusto.

In [`examples/automazioni_esempio.yaml`](examples/automazioni_esempio.yaml) trovi notifiche pronte: ricarica completata, batteria bassa fuori casa, riassunto serale.

## 🛠️ Servizi

```yaml
# Chiude subito il viaggio in corso
service: renault_ev_center.close_trip

# Azzera contatori (scope: km | energia | costi | viaggi | ricariche | all)
service: renault_ev_center.reset_counters
data: { scope: km }

# Registra una ricarica pubblica non misurata dalla wallbox
service: renault_ev_center.add_manual_charge
data: { kwh: 24.8, costo: 11.90, tipo: Pubblica }

# Esporta tutti i viaggi in CSV (config/renault_ev_center_export/)
service: renault_ev_center.export_trips_csv
```

## ❓ FAQ

**Come viene calcolato il tempo di viaggio?** Il viaggio si apre quando l'odometro aumenta e si chiude **dopo ~20 minuti senza movimenti** — in pratica quando **spegni l'auto** e odometro/posizione si aggiornano (il cloud Renault ha qualche minuto di ritardo). La durata registrata va dall'inizio all'**ultimo movimento rilevato**: la sosta post-viaggio non viene conteggiata. Finché l'auto è accesa il viaggio appare come "Trip Attivo" con dati provvisori.

**I sensori Renault restano "non disponibili" a volte.** È normale: il cloud Renault aggiorna lentamente. Mate tollera i buchi e riprende quando i dati tornano. Se vuoi un aiuto in più, esiste l'automazione classica di ricarica dell'integrazione Renault ogni ora.

**Le entità hanno ID diversi da quelli delle dashboard?** Le dashboard usano il prefisso del nome che hai dato all'auto in minuscolo. Rinomina l'entry o cerca/sostituisci nei file YAML.

**Posso avere due auto?** Sì: aggiungi una seconda istanza dell'integrazione con un altro nome.

**Dove sono i miei dati?** In `.storage/renault_ev_center.<entry_id>` — restano tuoi, nessun invio esterno.

## 🗺️ Roadmap / idee

- [ ] Salute batteria (SoH) stimata dalle ricariche piene
- [ ] Consumo notturno da fermo ("vampire drain")
- [ ] Invio dati ad **ABRP** (A Better Route Planner)
- [ ] Integrazione con l'Energy Dashboard di HA (ricariche casa)
- [ ] Card personalizzata dedicata

Hai un'idea? Apri una issue!

## 🤝 Crediti e disclaimer

- Ispirato a [LeapMotor Mate](https://github.com/ProtossBlaster/leapmotor-mate) e a TeslaMate.
- Richiede l'[integrazione Renault](https://www.home-assistant.io/integrations/renault/) di Home Assistant.
- Progetto **non ufficiale**, non affiliato a Renault. I dati dipendono dall'affidabilità dei sensori che configuri.

Licenza: **MIT** — vedi [LICENSE](LICENSE).

---

# 🇬🇧 English

**Trips, consumption, costs and charging for your Renault EVs — fully inside Home Assistant.**

A TeslaMate-style companion for **Megane E-Tech, Scenic E-Tech, Zoe, Twingo E-Tech and Alpine A290**, built on top of the official **Home Assistant Renault integration**. No extra accounts, no cloud, no code: install from HACS, pick your entities from dropdowns, done.

### Highlights

- **Automatic trip detection** from the odometer: distance, battery used, kWh, efficiency, auto-close after idle timeout
- **Charge sessions** with measured AC energy from your wallbox, SoC range, duration, type (Home/Solar/Public) and real cost
- **Costs**: €/km, €/100km, charge costs per day/week/month/year/all-time, separate home/public/solar tariffs
- **Meters**: daily/weekly/monthly/yearly km & energy with `last_period` attribute (utility_meter style)
- **Charging estimates**: time remaining, completion time, missing energy and estimated cost to your target SoC
- **Fuel comparison**: how much you saved vs your old diesel/petrol car
- **4 ready-made dashboards** (Overview, Trips, Statistics, Charging) — copy-paste YAML, core cards only
- Everything computed **locally** and persisted in `.storage`

### Install

1. HACS → Custom repositories → `https://github.com/Redrex/renault-ev-center` (category: Integration) → Download → restart HA
2. Settings → Devices & Services → Add Integration → **Renault EV Center**
3. Pick your Renault entities (odometer, battery %, range, charging, GPS) and wallbox entities (power, state, energy counter)
4. Import the dashboards from [`dashboards/`](dashboards/)

See the Italian section above for the full entity reference, services and FAQ — screenshots live in [`preview/index.html`](preview/index.html).
