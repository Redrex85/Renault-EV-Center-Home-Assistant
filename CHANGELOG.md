# Changelog

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
