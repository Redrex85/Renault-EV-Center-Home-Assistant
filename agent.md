# agent.md — Stato del progetto Renault EV Center

> Questo file è la **memoria di lavoro**: descrive cosa è stato fatto, cosa manca e come
> riprendere. Se una sessione si interrompe, leggi prima questo file, poi esegui
> `py tools/check_status.py` (dalla cartella del progetto) per vedere cosa non è ancora a posto.

---

## 1. Cos'è questo progetto

Integrazione **HACS per Home Assistant** ("Renault EV Center", dominio `renault_ev_center`)
per auto elettriche Renault (Megane/Scenic E-Tech, Zoe, Twingo, A290). Si appoggia
all'integrazione Renault ufficiale + sensori wallbox dell'utente e calcola:
viaggi automatici, ricariche con costi, contatori periodo, efficienza, risparmio vs termica,
salute batteria (SOH), report tabelle, filtri ricariche. Nessun cloud: tutto locale in `.storage`.

**Nome entità**: prefisso = nome auto scelto in configurazione (default `Renault` → `sensor.renault_*`).

## 2. COMPLETATO ✅

### Integrazione (`custom_components/renault_ev_center/`)
- [x] Rinomina completa da "Renault EV Mate" → "Renault EV Center" (domain, cartelle, file)
- [x] Prefisso entità default `renault_` (DEFAULT_NAME = "Renault")
- [x] `config_flow.py`: wizard 3 step (auto → wallbox → impostazioni) + options flow
- [x] `coordinator.py`: polling entità sorgente, contatori periodo km/energia/costi
      (replica utility_meter con `last_period`), motore viaggi (timeout, filtri, arricchimento
      con `costo_stimato` e `carica_precedente`), sessioni di ricarica (Casa/FV/Pubblica),
      prezzi dinamici letti dai number, filtri ricariche dai select, report
      Generale/Settimanale/Mensile, salute batteria (efficienza ≤100%, perdite, SOH stimato)
- [x] `sensor.py` (~45 sensori): efficienza, batteria kWh, kWh totali, %/100km, contatori
      km/energia/costi con last_period, stime ricarica, tipo ricarica, viaggi (attivo, ultimo,
      oggi, statistiche 7/30/90, archivio completo), lista ricariche filtrata, report generale,
      ultima ricarica, risparmi vs diesel, wallbox potenza, efficienza/perdite/SOH stimato
- [x] `binary_sensor.py`: in carica, wallbox in carica
- [x] `button.py`: chiudi viaggio, esporta CSV, reset km/energia/costi
- [x] `number.py`: costo casa/colonnina/FV, capacità, obiettivo %, **SOH ufficiale**
      (con RestoreEntity, precedenza sui valori di configurazione)
- [x] `select.py`: filtro tipo ricarica (Tutte/Casa/Fotovoltaico/Pubblica), filtro periodo
      (Settimana/Mese/Anno/Tutto)
- [x] `store.py`: persistenza viaggi/ricariche/storico/contatori/**health**
- [x] `services.yaml` + servizi: close_trip, reset_counters, export_trips_csv,
      add_manual_charge, delete_trip
- [x] `strings.json` + traduzioni `it.json` / `en.json`
- [x] Tutti i moduli compilano (`py_compile` OK)

### Dashboard (`dashboards/`, prefisso `sensor.renault_*`)
- [x] `01_panoramica.yaml` — stile dashboard esistente dell'utente: picture-elements con foto
      auto (`/local/renault-ev-center/auto.png`), bar-card batteria, tile posizione/risparmio,
      efficienza, costi, stato ricarica, comandi Renault (A/C, carica), apexcharts km+consumi,
      mini-graph wallbox, mappa, ultima ricarica
- [x] `02_viaggi.yaml` — albero **Anno → Mese → Giorno** stile LeapMotor (markdown Jinja con
      groupby/selectattr) + tabella dettaglio con Spesa e "Ricarica prima"
- [x] `03_statistiche.yaml` — tabelle **Generale / Settimanale / Mensile** (come screenshot
      utente) + metric mese/anno + trend 30gg/12mesi + report mensile
- [x] `04_ricariche.yaml` — **filtri** (2 select) + lista filtrata con **totali kWh/€/€kWh** +
      energie/spese per periodo + stato wallbox
- [x] `05_salute_batteria.yaml` — gauge SOH ufficiale/stimato, efficienza, perdite, sessioni
- [x] `06_impostazioni.yaml` — number prezzi/capacità/obiettivo/SOH + pulsanti reset/export
- [x] YAML tutti validi; coerenza entità↔dashboard verificata da script (68 entità OK)

### Altro
- [x] `examples/automazioni_esempio.yaml` (notifiche)
- [x] `docs/INSTALLAZIONE.md` (IT) e `docs/INSTALLATION.md` (EN)
- [x] `hacs.json` (min HA 2025.11), `manifest.json`, `LICENSE` MIT, `CHANGELOG.md`, CI validate
- [x] Script di verifica in `%TEMP%\opencode\`: `validate_yaml.py`, `check_entities2.py`,
      `check_py.py` (ricreabili — vedi tools/check_status.py)

## 3. DA FARE / DA SISTEMARE ⚠️

- [ ] **Test su HA reale** (l'utente può farlo sul suo HA di produzione: l'integrazione è
      additiva e non tocca i package esistenti): installare, configurare con i propri sensori
      (sensor.mileage, sensor.battery_level, sensor.battery_autonomy, binary_sensor.charging,
      device_tracker.location, wallbox: sensor.wallbox_instant_power, sensor.wallbox_charger_state,
      contatore energia), verificare che i viaggi si chiudano e i costi si accumulino.
- [ ] **GitHub**: creare repo `renault-ev-center`, push, release v1.1.0, aggiungere screenshot
      reali in `docs/screenshots/` e linkarli nel README. Sostituire "Redrex" con l'username reale.
- [ ] *(Opzionale, futuro — vedi sezione 5 per le idee)*: card Lovelace dedicata, invio ABRP,
      vampire drain, Energy Dashboard, statistiche per zona.

### Fatto nella sessione 22 (card: dati oggi + testo più grande) ✅
- [x] **Card dedicata** (JS reale + mock preview): "kWh a bordo" e odometro ingranditi
      (13.5px semibold), aggiunta riga **"% consumata oggi"** e **"kWh usati oggi"**
      (sensori batteria_scaricata_oggi / energia_batteria_giornaliera).
      JS sincronizzato in custom_components/.../www/ (copiato in /config/www al setup).
- [x] Preview: preview/index_v13.html (index.html bloccato — apri direttamente index_v13.html).

### Fatto nella sessione 21 (fix panoramica preview v12) ✅
- [x] **Panoramica preview riscritta da zero** (la v11 era impaginata male per confini
      div sbagliati nell'estrazione): ordine corretto e pulito —
      1. Card dedicata (foto, batteria, odometro, km oggi)
      2. Stato ricarica + comandi (+ wallbox W)
      3. Efficienza + Ultima ricarica + Mappa
      4. Risparmio netto
      poi Oggi a colpo d'occhio e grafico 7 giorni.
- [x] HTML bilanciato verificato; file: preview/index_v12.html (index.html bloccato —
      chiudere tab, cancellare index.html, rinominare index_v12.html).

### Fatto nella sessione 20 (panoramica riordinata) ✅
- [x] **Panoramica riordinata** (preview v11 + YAML live, stesso ordine):
      1. Card dedicata (con odometro e km oggi già integrati nella card JS)
      2. Stato ricarica + comandi Renault
      3. Efficienza + Ultima ricarica + Mappa
      4. Riepilogo Risparmi (netto)
      poi: Oggi a colpo d'occhio, grafico consumi, Tagliandi.
      Rimossa la card Batteria ridondante (autonomia/odometro duplicati).
- [x] preview/index_v11.html (index.html bloccato dal browser — solito swap).
- [x] YAML riordinato via round-trip (header commenti preservato), bundlate sincronizzate.
- [x] check_status 84 OK.

### Fatto nella sessione 19 (preview finale v10 con profili) ✅
- [x] **Selettore profili Minimal/Pro/Enterprise INTERATTIVO** in Impostazioni:
      nasconde/mostra davvero Gestione ricarica, tabelle wallbox, report solare (FV),
      carica programmata — demo dal vivo dei 3 profili.
- [x] Automazioni: % minima, fascia oraria, orari e % di avvio/stop ora **input editabili**
      nel preview (in HA sono le entità number/time reali).
- [x] Viaggi: card "doppia verifica" + colonna Verifica (✅ / ⚠️ gps in ritardo).
- [x] File: preview/index_v10.html (index.html ancora bloccato dal browser).
- [x] HTML verificato bilanciato.

### Fatto nella sessione 18 (archivio mensile permanente) ✅
- [x] **Archivio mensile permanente** (idea utente): ogni tick i km del mese corrente
      vengono salvati in store (`monthly_km["YYYY-MM"]`); al cambio mese il mese chiuso
      viene **congelato**. La tabella Mensile/Storico (e Report solare) legge i km
      **dall'archivio** quando esiste → lo storico di **tutti gli anni passati** funziona
      per sempre anche oltre i 365 giorni dello storico giornaliero. Costi e kWh restano
      live dalla lista ricariche (così ricariche manuali tardive vengono comunque conteggiate).

### Fatto nella sessione 17 (preview interattiva v9) ✅
- [x] **Preview**: toggle automazioni CLICCABILI (on/off visivo) e tabella Mensile con
      **menu anno funzionante** (2025/2026/2027 — cambia davvero i dati e il TOTALE).
      Nota: nel preview è simulazione; in HA è pilotato dal selettore
      "Filtro Anno Ricariche" e dagli switch reali dell'integrazione.
- [x] File: preview/index_v9.html (index.html bloccato dal browser — chiudere la tab,
      cancellare index.html, rinominare index_v9.html; puliti i vecchi v7/v8).
- [x] Catena build riparata (v8 era partita da un index obsoleto).

### Fatto nella sessione 16 (priorità batteria + report solare + preview v8) ✅
- [x] **Priorità batteria casa** nel bilanciamento: config aggiunge **sensore SoC batteria**
      e slider "SoC minimo prima di dare surplus all'auto" (number "Priorita Batteria Casa"
      regolabile in Gestione ricarica). Sotto soglia → surplus solo da esportazione rete,
      scarica batteria esclusa (la casa carica prima). Il sensore **potenza** batteria
      resta opzionale (serve solo se si vuole usare anche la sua scarica come surplus).
- [x] **Report solare** in Storico ricariche: tabella mese per fonte (casa/FV/colonnine/tot)
      per l'anno selezionato + TOTALE.
- [x] **Preview v8** (`index_v8.html` — index.html ancora bloccato dal browser): 11 pagine
      con nuova tab Gestione ricarica, Storico ricariche rinominato, report solare,
      slider priorità. UTENTE: chiudere tab, cancellare index.html, rinominare index_v8.html.
- [x] check_status 84 OK.

### Fatto nella sessione 15 (profili + gestione ricarica + bilanciamento) ✅
- [x] **Profili installazione**: Minimal (solo auto) · Pro (auto+wallbox) · Enterprise
      (auto+wallbox+FV). Nel wizard wallbox: toggle "Ho il fotovoltaico" + sensori
      bilanciamento (rete W, batteria W opz., inverti segno, includi batteria, W/A).
- [x] **Dashboard adattiva al profilo**: il builder filtra le sezioni wallbox/gestione/
      carica programmata quando non c'è wallbox (Minimal); la vista Gestione ricarica
      esiste solo con wallbox.
- [x] **Nuova vista "Gestione ricarica"** (12): controllo wallbox, potenza/tempi,
      % obiettivo, ampere wallbox (segnaposto da mappare), **bilanciamento solare**
      (switch on/off + ampere min/max) e carica programmata.
- [x] "Ricariche" rinominata **"Storico ricariche"**.
- [x] **Bilanciamento solare nativo** (adattato dall'automazione utente, con migliorie):
      surplus = -rete (+ batteria opzionale), correzione = surplus/W-per-ampere,
      clamp min/max, isteresi 1 A, deadband 100 W, pausa min 60 s tra cambi,
      notifica opzionale. Scrive sul number corrente wallbox mappato.
      Stato esposto negli attributi di "Wallbox Potenza".
- [x] Nuove entità: switch Bilanciamento Solare, number Ampere Minimi/Massimi.
- [x] check_status **84 OK**. Migliorie vs automazione originale: isteresi/deadband
      (niente oscillazioni), pausa 60 s, limiti da entità modificabili, segno sensore
      configurabile, notifica disaccoppiata (usa notify generale).

### Fatto nella sessione 14 (card in panoramica + index v7) ✅
- [x] **01_panoramica.yaml**: sostituito picture-elements+bar-card con la **card dedicata**
      `custom:renault-ev-center-card` (foto auto al posto del logo). Richiede registrazione
      risorsa una volta: /local/renault-ev-center/renault-ev-center-card.js.
- [x] **Preview v7** (index_v7.html — index.html era bloccato dal browser): panoramica con
      mock della card dedicata + "Oggi a colpo d'occhio", Ricariche con Mensile-per-anno
      (+ TOTALE), Statistiche con Rotte avanzate. HTML verificato bilanciato.
      UTENTE: chiudere la tab del browser su index.html → cancellarlo → rinominare
      index_v7.html → index.html.
- [x] check_status 82 OK.

### Fatto nella sessione 13 (card dedicata + rotte avanzate) ✅
- [x] **Card Lovelace dedicata** `renault-ev-center-card.js` (www/ + bundlata in
      custom_components/…/www/, copiata automaticamente in /config/www al setup):
      auto con overlay autonomia/carica, barra batteria colorata per soglie, kWh a bordo,
      odometro, pannello carica (tipo + kW wallbox) o viaggio in corso, 4 mini-tile
      (km/kWh, kWh/100km, km oggi, €/km). Registrazione risorsa:
      /local/renault-ev-center/renault-ev-center-card.js → tipo custom:renault-ev-center-card.
- [x] **Demo visibile nel browser**: preview/card_demo.html carica il JS reale con dati fittizi.
- [x] **Statistiche per zona avanzate**: rotte con km_medio e **costo** (kWh × prezzo casa),
      **migliore/peggior rotta** per efficienza (attrs + sezione "Rotte avanzate" in Statistiche).
- [x] Energy Dashboard esteso (sessione precedente): sensori casa + FV total_increasing.
- [x] check_status **82 OK**. ABRP: spiegato (bridge API tlm/send), da implementare su richiesta.

### Fatto nella sessione 12 (panoramica oggi + totali) ✅
- [x] **Panoramica**: nuova sezione "Oggi a colpo d'occhio" — Consumata oggi (%),
      Ricaricati oggi (kWh + %), kWh usati oggi, Ricariche oggi (€), Km oggi,
      Ricariche mensili (€) e **Consumo istantaneo wallbox in W**.
- [x] **Ricariche**: righe **TOTALE** sotto le tabelle Settimanale e Mensile
      (costo/kWh/km sommati; il totale mensile segue il Filtro Anno selezionato).
- [x] Dashboards bundlate sincronizzate; check_status **79 OK**.

### Fatto nella sessione 11 (automazioni regolabili da dashboard) ✅
- [x] **Parametri automazioni ora entità inline**: number "Batteria Minima Promemoria (%)",
      "Carica Avvio Sotto (%)", "Carica Ferma Sopra (%)" + nuova piattaforma **time** con
      "Promemoria Inizio/Fine" e "Carica Orario Avvio/Stop" (RestoreEntity, registrate nel
      coordinator). Il motore automazioni legge i valori DINAMICI ad ogni tick:
      si cambia tutto dalla vista Automazioni senza toccare la configurazione.
- [x] Vista 10_Automazioni riscritta: sezioni con switch + % + orari per ciascuna
      automazione (avvio, fine, promemoria, carica programmata) con spiegazioni.
- [x] Risposta alla domanda: le automazioni native replicano quelle dei package utente
      (avvio ricarica, fine ricarica con kWh/SoC/costo dal loro charging_session_complete)
      più promemoria % e carica programmata (nuove).
- [x] check_status **77 OK**.

### Fatto nella sessione 10 (mensile per anno) ✅
- [x] **Ricariche → Mensile dinamica per anno**: la tabella Gennaio→Dicembre segue il
      **Filtro Anno** (2025 → mesi del 2025, 2026 → 2026, anni successivi inclusi).
      Costo, kWh caricati e km per ogni mese; il mese corrente usa anche i dati live.
      Il report espone l'anno selezionato come attributo `anno` (mostrato nel titolo).

### Fatto nella sessione 9 (doppia verifica viaggi + fix preview) ✅
- [x] **Doppia verifica viaggi**: chiusura ANTICIPATA quando si collega la carica
      (spina = arrivo certo, campo verifica="chiuso anticipato"); a chiusura salvate
      le **coordinate GPS reali** del tracker (`gps_arrivo`) — coprono il caso in cui
      la posizione si aggiorna nel punto esatto ma fuori dalle zone di HA;
      flag `verifica` = "ok" / "gps non aggiornato (cloud in ritardo)".
      Attributi esposti anche su "Ultimo Trip".
- [x] **Fix preview index.html**: la v6 aveva perso footer/chiusura .main/script
      (i clic non funzionavano) — ripristinati, HTML bilanciato verificato.
      NOTA: index.html era bloccato dal browser → versione corretta in
      `preview/index_v6.html` (chiudere la tab, cancellare index.html, rinominare).
- [x] check_status 75 OK; dashboards bundlate sincronizzate.

### Fatto nella sessione 8 (fix dashboard + wallbox start/stop) ✅
- [x] **Fix creazione dashboard automatica**: API Lovelace adattive (sync/async, più getter),
      verifica e **piano B**: se qualcosa fallisce scrive il dashboard pronto in
      `/config/renault-ev-center_<nome>_dashboard.yaml` + notifica persistente con le
      istruzioni di incolla. Nuovo servizio `renault_ev_center.create_dashboard` per riprovare.
- [x] **Avvio/stop carica programmata via WALLBOX**: nuovo campo config
      "Entità avvio/stop carica wallbox" (switch → turn_on/turn_off, button → press);
      fallback al number target Renault per lo stop.
- [x] **Documentato il calcolo del tempo di viaggio** (README FAQ + card in dashboard Viaggi):
      si apre all'aumento odometro, si chiude ~20 min dopo l'ultimo movimento (spegnimento
      auto + aggiornamento sensori); la durata NON include la sosta post-viaggio; mentre
      l'auto è accesa il viaggio è "Trip Attivo" con dati provvisori.
- [x] Dashboards bundlate sincronizzate (10 file); check_status **75 OK**.

### Fatto nella sessione 7 (installazione automatica + automazioni) ✅
- [x] **Dashboard automatica**: alla configurazione l'integrazione crea la plancia laterale
      "«Nome» EV Center" (icona auto) con tutte le 10 viste incluse, prefisso entità
      adattato al nome scelto (opzione "Crea dashboard" disattivabile). File viste
      bundlati in custom_components/renault_ev_center/dashboards/.
- [x] **Foto per modello**: scelta modello nel wizard (Megane/Scenic E-Tech, Zoe,
      Twingo, A290, Custom) → immagine copiata in /config/www/renault-ev-center/auto.png
      (placeholder inclusi in images/, sostituibili con foto reali).
- [x] **Automazioni integrate** (vista 10 + switch + motore nel coordinator):
      notifica avvio ricarica, notifica fine ricarica (kWh/SoC/costo), promemoria
      batteria bassa a casa (% e fascia oraria configurabili), carica programmata
      (orario o %, avvio via pulsante Renault, stop via number target).
      Servizio notify e giorni preavviso nel config flow.
- [x] Rinomine: "Costo fotovoltaico" (ex FV/BEB) e "Obiettivo Ricarica".
- [x] **Statistiche**: rimosse tabelle Generale/Mensile (solo in Ricariche); aggiunta
      sezione Anno→Mese + grafici Km/giorno, trend efficienza, energia per giorno.
- [x] **Palette colori Renault**: Blu Megane (default), Giallo R5, Verde R4,
      Grigio Aviation — selettore spostato nel tab Impostazioni; temi HA aggiornati
      (renault-blu/giallo/verde/aviation/luce).
- [x] preview v6 in preview/index.html; check_status **75 controlli OK**.

### Fatto nella sessione 6 (palette blu + manutenzione evoluta) ✅
- [x] **Blu elettrico predefinita** (preview e temi).
- [x] **Panoramica tornata al layout precedente** + foto auto personalizzabile
      (/local/renault-ev-center/auto.png) + tasti Stato ricarica/Zona/Presa/Avvia A/C/
      Avvia carica/Fine ricarica + mappa spostamenti.
- [x] **Manutenzione divisa in Tagliandi e Assicurazione**: costo assicurazione (number),
      rinnovo +6 mesi/+1 anno/data precisa (servizio renew_insurance), scadenze dinamiche
      in store (set_scadenza), **tagliando a scelta per km o per data** (set_tagliando),
      **notifica scadenze su Telegram** con scelta del servizio notify.* e giorni di
      preavviso (config flow; una notifica al giorno fino alla scadenza).
- [x] **Salute batteria**: rimossi i gauge grandi; SOH ufficiale impostabile inline (tile number).
- [x] **Ricariche**: aggiunte tabelle Generale/Settimanale/Mensile (dati wallbox).
- [x] **Statistiche**: tile stile LeapMotor (totale viaggi, distanza, avg/best efficienza,
      tempo guida, energia usata, ricariche, energia caricata) + **differenziazione
      casa/FV/colonnine** + tabella **Percorrenza** (% usata, usati, caricati, km per
      oggi/ieri/settimana/mese/anno + periodi precedenti) + efficienza media.
- [x] **Nuova vista Risparmi** (09): carburante, termica teorica, tagliandi (termica 450 €
      default − spesa reale), bollo, netto, FV mese; riassunto compatto resta in Panoramica.
- [x] preview v5 = `preview/index_v5.html` (index.html era bloccato dal browser:
      chiudere la tab, cancellare index.html e rinominare index_v5.html → index.html).
- [x] check_status: **67 controlli OK**.

### Fatto nella sessione 5 (release 1.0.0) ✅
- [x] **Vista Manutenzione** dedicata (`08_manutenzione.yaml`): prossimo tagliando con
      semaforo, spesa reale EV, risparmio manutenzione (teorica termica − reale), storico.
- [x] **Risparmio tagliandi con spesa reale**: usa il registro `add_maintenance`
      (formula: n. tagliandi termici × costo termico − spesa reale EV), dettaglio negli
      attributi del sensore e nel box Risparmi.
- [x] **4 palette proposte** con anteprima interattiva (selettore nel preview):
      Jaune (grafite+giallo, default), Blu elettrico, Arancio grafite, Luce.
      Temi HA equivalenti in `/themes` (renault-jaune, renault-blu, renault-luce).
- [x] **Versione v1.0.0** nel preview + manifest; CHANGELOG unificato alla 1.0.0.
- [x] **Panoramica** completa: foto auto, stato ricarica, zona ricarica, avvia A/C,
      avvia carica, stato presa, **mappa spostamenti** con posizione attuale.
- [x] preview/index.html rigenerato v4 (8 tab) — swap riuscito.

### Fatto nella sessione 4 (extra) ✅
- [x] Lista ricariche stile app Renault: **Δ SoC** e **Ø kW** per sessione, totali con
      **ore e Ø kW**, kW live in "Ultima sessione" (dati `potenza_media_kw` già nei record)
- [x] **7 extra implementati** (vista `07_extra.yaml` + config flow): vampire drain,
      consumo per zona (rotte), meteo vs consumi (sensore temperatura opzionale),
      CO₂ risparmiata (fattori configurabili), scadenze bollo/revisione/assicurazione,
      viaggio Top&Stop del mese, sensore Energy Dashboard "Energia Caricata Casa (totale)"
- [x] check_status.py aggiornato: **60 controlli OK**
- [x] CHANGELOG 1.2.0
      (il vecchio index.html è bloccato dal browser). Quando chiudi la tab del browser:
      Contiene: box Risparmi + Tagliandi in Panoramica, Statistiche stile LeapMotor,
      Ricariche con filtri tipo/periodo/**anno** + ØkW/Δ%, Salute completa, tab Extra.

### Fatto nella sessione 3 (v1.1.0) ✅
- [x] preview/index.html nuova versione 6 tab con logo originale bianco (solo simbolo,
      sfondo trasparente) — `preview/logo_renault.png` + `docs/images/logo_renault_symbol.png`
- [x] README aggiornato (funzionalità, 6 dashboard, card custom, prefisso renault_)
- [x] CHANGELOG 1.1.0
- [x] Box **Risparmi** in Panoramica: carburante + tagliandi evitati + bollo + NETTO
- [x] **Prezzo carburante dinamico**: campo opzionale "Sensore prezzo carburante" nel
      config flow (se impostato usa il prezzo live, altrimenti quello fisso)
- [x] **Registro Tagliandi**: servizio add_maintenance/delete_maintenance, sensore
      `renault_tagliandi` (costo totale, prossimo a km), card in Panoramica
- [x] **Statistiche stile LeapMotor**: tile Da sempre (viaggi, distanza, migliore efficienza,
      ore guida) + mese + trend 30gg/12mesi + tabelle Generale/Settimanale/Mensile
- [x] **Ricariche**: filtro **Anno** (Tutti/2024…2032), breakdown ultima sessione
      (rete/batteria/dispersa), lista completa con totali
- [x] **Salute batteria**: SOH ufficiale modificabile inline, **kWh per 1% batteria**
      (capacità×SOH/100), breakdown rete/batteria/dispersa
- [x] check_status.py: 58 controlli OK

## 4. Come riprendere (procedure)

```powershell
# 1. stato del progetto
cd \\nas\HDD3TB2\HA\renault-ev-center
py tools\check_status.py

# 2. se "py_compile ERR" → apri il file indicato e correggi
# 3. se "YAML ERR"  → correggi il dashboard/manifest indicato
# 4. se "COERENZA: PROBLEMI" → allinea i nomi entità tra sensor.py e dashboards/
# 5. rileggi la sezione 3 qui sopra e spunta i completati
```

Regole del progetto:
- Nomi entità = f"{NomeAuto} {Etichetta}" (has_entity_name=False); slugify HA: minuscolo,
  spazi→_, simboli rimossi. NON usare "%" o "/" nei nomi se cambia lo slug atteso.
- I prezzi/target/capacità/SOH vivono nei **number** (hanno precedenza sulla config).
- Filtri ricariche nei **select**; il calcolo filtrato è in `coordinator._filter_charges`.
- Report tabelle in `coordinator._build_report` → sensore `renault_report_generale`.
- Salute batteria in `coordinator._finalize_charge` (solo ricariche Casa misurate da wallbox).
- Ogni modifica a sensor.py → aggiornare anche la lista attesa in tools/check_status.py.
- **Versioning (OBBLIGATORIO ad ogni modifica)**: bump del **patch** `1.0.5.x` (4° numero)
  a ogni commit di modifica. Il **3° numero** (1.0.5 → 1.0.6) lo alza SOLO l'utente quando
  decide. Aggiornare SEMPRE e TUTTI insieme:
  `VERSION`, `custom_components/renault_ev_center/manifest.json` (`"version"`),
  badge in `custom_components/renault_ev_center/www/renault-ev-center-panel.js` (`.ver`),
  console in `custom_components/renault_ev_center/www/renault-ev-center-card.js`,
  e `preview/index.html` (title + badge). Verifica finale: `py tools\check_status.py`
  deve dare `manifest version = VERSION`.

## 5. Scelte fatte (per coerenza futura)

- Nome: **Renault EV Center**, dominio **renault_ev_center**, repo suggerito `renault-ev-center`.
- Default auto: "Renault" (l'utente può scegliere altro nome per multi-auto).
- Tipi ricarica: Casa / Fotovoltaico / Pubblica (zona FV configurabile, default "beb").
- Efficienza = teorica(Δ%×kWh-per-1%)/misurata wallbox, limitata a 100; SOH stimato solo con Δ%>5.
- kWh per 1% = capacità × SOH ufficiale / 100 (number `renault_soh_ufficiale`).
- Costo viaggio = kWh viaggio × prezzo casa corrente; "Ricarica prima" = tipo ultima ricarica
  conclusa prima della partenza del viaggio.
- Risparmio netto = carburante evitato + tagliandi evitati (km/intervallo × differenza costo
  tagliando) + bollo (anni stimati × differenza bollo). Anni stimati = km_totali/15000.
- Prezzo carburante: se configurato il sensore `diesel_price_entity` usa il prezzo live,
  altrimenti il prezzo fisso della configurazione.
- Filtro anno ricariche: select con opzioni fisse "Tutti" + 2024…2032.
- Dashboard usano card core + bar-card + apexcharts-card + mini-graph-card (già installate
  dall'utente); requisito minimo HA 2025.11 (card metric).

## 6. Idee proposte all'utente (da confermare prima di implementare)

1. **Vampire drain**: % persa da fermo nelle ultime 24h (serve odometro fermo + SoC).
2. **Consumo per zona**: km/kWh medi per zona (casa→lavoro) usando lo storico viaggi.
3. **Meteo vs consumi**: correlazione con sensore temperatura esterna (già in HA).
4. **CO2 risparmiata**: kg CO2 evitati vs auto termica (fattore emissivo configurabile).
5. **Energy Dashboard**: esporre "energia caricata a casa" come dispositivo griglia.
6. **Promemoria scadenze**: bollo/revisione/assicurazione con input_datetime.
7. **Best/worst trip**: viaggio più efficiente/peggiore del mese.
8. **Notifica "carica completa alle XX:XX"** con orario previsto già a inizio carica.
