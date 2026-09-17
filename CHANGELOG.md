# Changelog

Release accorpate: **1.0.4 · 1.0.3 · 1.0.1 · 1.0.0** — le patch `1.0.3.x` / `1.0.4.x`
non esistono più come release separate.
La serie **1.0.5** è ancora attiva come `1.0.5.x`; verrà accorpata in un unico tag `1.0.5`
al passaggio alla **1.0.6** (workflow *Collapse release series*).

## 1.0.5 — Pannello EV Center, Wallbox e rifiniture

### Pannello Lovelace (`renault-ev-center-panel.js`)
- Pannello completo a **11 pagine**: Panoramica, Viaggi, Statistiche, Ricariche,
  Salute batteria, Manutenzione, Risparmi, Extra, Automazioni, Impostazioni, **Wallbox**.
- Sensori cliccabili → more-info di Home Assistant; date `gg-mm-aaaa`; zone leggibili;
  selettore tema (pulsante palette) + navigazione laterale e mobile.

### Wallbox (nuova pagina)
- Live: **stato**, potenza, corrente, tensione, temperatura, motivo limite.
- **Tempo sessione** e **kWh sessione**: entità prese dalla configurazione, con fallback
  al **contatore interno** (parte oltre la soglia W) e ai sensori Lektrico; formattazione
  adattiva **secondi/minuti/ore**.
- **Limite di carica in A** (slider sul `number` mappato) e **avvio/stop** ricarica.
- **Bilanciamento solare** (switch + surplus/rete/ampere) e **bilanciamento casalingo**
  (automazioni HA con "wallbox" nel nome).

### Manutenzione · Risparmi · Extra · Automazioni
- Manutenzione: Tagliando e Cambio gomme affiancati, **registro interventi** con elimina,
  form d'inserimento compatto; scadenze da ultima manutenzione + intervallo km.
- Risparmi: mese/anno, bollo e **costo totale ricariche** letti dai sensori reali.
- Extra: Meteo a piena larghezza, **CO₂ evitata**, scadenze; rimosse card ridondanti.
- Automazioni: notifiche, programma ricarica/clima, promemoria batteria bassa e nuova
  **"Notifica avvio ricarica"** (trigger sull'entità stato wallbox mappata in configurazione),
  create da *Impostazioni → Crea automazioni consigliate* in `automations.yaml`.

### Correzioni
- Contatori giornalieri **dimezzati**: baseline ancorata all'odometro; workaround `max(contatore, viaggi)`.
- **Giorno sbagliato** per l'early-exit del coordinator (aggiunta chiave `daily`).
- `DeltaMeter`: direzione "down" ripristinata + auto-heal; `button.press` ora fa refresh.
- **Trip engine** seed-based: niente viaggi fantasma ad auto ferma; chiusura su arrivo/GPS.
- Mappa spostamenti via card nativa; rimossi i sottotitoli `.sub`; numeri `data-dec`.

## 1.0.4 — Pannello Lovelace e servizi

- Introdotto il **pannello Lovelace** (`www/renault-ev-center-panel.js`, vista `panel`)
  registrato dalla dashboard laterale.
- `dashboard.py` riscritto; `RELAZIONE_INTEGRAZIONE.md`; nuovi servizi in `services.yaml`;
  `strings.json` + traduzioni **it** ampliati.
- Card JS `renault-ev-center-card.js`; preview aggiornata.

## 1.0.3 — Branding, icone e documentazione

- Aggiunti **brand assets** (`brand/icon.png`, `icon@2x`, logo) e icona HACS + `icon.png`.
- **README** ampliato (guida completa, funzionalità, esempi); docs d'installazione (IT/EN/FR).
- `__init__.py` esteso; allineamento traduzioni **en**/**fr**; workflow `validate` aggiornato.
- *(Assorbe la 1.0.2.)*

## 1.0.1 — Correzioni bug

- **Import mancanti**: aggiunti `DOMAIN` e `CONF_WB_MAX_CURRENT` in `coordinator.py`;
  costanti notifiche/manutenzione in `config_flow.py` (evitati `NameError` in caricamento,
  config flow e bilanciamento solare).
- **Number collegati ai calcoli**: prezzi casa/colonnina/FV, capacità, obiettivo % e costo
  assicurazione ora letti dalle entità number della dashboard (fallback ai valori config).
- **Early-exit**: il controllo "niente è cambiato" include ora switch/time/select/number,
  quindi le automazioni partono subito dopo la modifica delle impostazioni.
- **Carica programmata**: corretta la finestra notturna (es. 23:30 → 07:00) con helper
  `_in_window()`; start/stop ora usano la stessa finestra.
- **Switch**: la variazione richiede subito un refresh del coordinator.
- **Number `balance_max_amps`**: corretta la chiave iniziale (`balance_max_amps`).
- **Traduzioni**: `options` spostato a livello radice in `en.json`/`fr.json` (hassfest
  lo rifiuta dentro `config`); workflow `validate` aggiornato a `checkout@v5` /
  `setup-python@v6` (deprecation Node 20).
- Rimossi import duplicati; aggiunto file `VERSION`; checker versione aggiornato.

## 1.0.0 — Prima release pubblica

Prima versione completa di **Renault EV Center**, integrazione HACS per le Renault elettriche.

### Motori e calcoli
- Rilevamento **viaggi automatico** dall'odometro con chiusura per timeout, kWh, efficienza,
  costo stimato e fonte dell'ultima ricarica prima della partenza.
- **Sessioni di ricarica** con energia wallbox (AC), SoC iniziale→finale, durata, **Ø kW**,
  tipo (Casa/Fotovoltaico/Pubblica) e costo reale; ricariche manuali per le colonnine DC.
- Contatori **km / energia / costi** per giorno/settimana/mese/anno con `last_period`.
- Efficienza live (km/kWh, kWh/100km), costi €/km e €/100km, stime ricarica (tempo,
  completamento, costo verso il % obiettivo).
- **Risparmio netto** vs auto termica: carburante (con prezzo live opzionale da sensore),
  **tagliandi con spesa reale** (registro manutenzioni) e **bollo**.
- **Salute batteria**: efficienza ricarica (mai >100%), breakdown rete/batteria/dispersa,
  SOH stimato dalle ricariche a casa, **SOH ufficiale** concessionaria, **kWh per 1%**.
- **Extra**: vampire drain, consumo per zona (rotte), meteo vs consumi, CO₂ risparmiata,
  scadenze (bollo/revisione/assicurazione), viaggio Top&Stop del mese,
  sensore **Energy Dashboard** ("Energia Caricata Casa (totale)").
- Report tabelle **Generale / Settimanale / Mensile**; storico giornaliero 365 giorni.

### Configurazione e controllo
- Wizard in 3 schermate (auto → wallbox → impostazioni) con selettori di entità; opzioni
  modificabili dopo. Prefisso entità = nome auto (default `renault_`).
- **Number** in dashboard: prezzi casa/colonnina/FV, capacità, obiettivo %, SOH ufficiale.
- **Select** filtri ricariche: tipo, periodo e **anno** (Tutti/2024…2032) con totali automatici.
- Servizi: close_trip, reset_counters, export_trips_csv, add_manual_charge, delete_trip,
  add_maintenance, delete_maintenance. Pulsanti rapidi e notifiche d'esempio.

### Dashboard (8 viste) e temi
- Panoramica (foto auto, sensori Renault, comandi, mappa spostamenti, box Risparmi),
  Viaggi ad albero Anno→Mese→Giorno, Statistiche stile LeapMotor, Ricariche stile app,
  Salute batteria, **Manutenzione**, Extra, Impostazioni.
- **3 temi inclusi** (`/themes`): renault-jaune, renault-blu, renault-luce.
- Logo Renault (marchio di Renault S.A.S., uso descrittivo).
