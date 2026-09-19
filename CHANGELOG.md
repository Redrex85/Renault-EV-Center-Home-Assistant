# Changelog

Release accorpate: **1.0.4 · 1.0.3 · 1.0.1 · 1.0.0** — le patch `1.0.3.x` / `1.0.4.x`
non esistono più come release separate.
La serie **1.0.5** è ancora attiva come `1.0.5.x`; verrà accorpata in un unico tag `1.0.5`
al passaggio alla **1.0.6** (workflow *Collapse release series*).

## 1.0.19 — Sperimentazione GSE + automazioni

### Nuova funzione: limite di potenza a fasce orarie (GSE)
Interruttore **Sperimentazione GSE** (tra i dispositivi, o nella pagina *Wallbox*). Quando è
**attivo**, durante la carica la wallbox viene limitata automaticamente:

| Momento | Potenza |
|---|---|
| Feriali **23:00 → 07:00** | **piena** (default 6 kW) |
| **Domenica** (e festivi, se mappati) | **piena** 24 h |
| Tutti gli altri orari | **ridotta** (default 3 kW) |

- Configurazione in *Configura → ⚡ Sperimentazione GSE*: potenza piena, potenza ridotta,
  inizio/fine fascia, "domenica 24 h", sensore **festivi** opzionale, e **W/A della wallbox**
  (230 monofase · 690 trifase) per convertire kW → ampere.
- Agisce sul `number` **corrente massima wallbox** già mappato; non fa nulla se è già corretto.
- Nel pannello (*Wallbox*) vedi **limite adesso** (piena/ridotta) e la fascia configurata.
- Controllo `check_status.py` **[21]**: domenica, in fascia, dopo mezzanotte, fuori fascia.

### Correzioni (automazioni)
- **"Messaggio fine carica" mai inviato**: l'automazione aveva una condizione che confrontava la
  **data d'inizio** della ricarica con **oggi** → una carica notturna (inizia ieri, finisce oggi)
  veniva **scartata**. Condizione rimossa.
- **Trigger su entità sbagliata**: l'automazione scattava sull'entità *sorgente* (che può essere un
  sensore testuale `charging`/`not_charging`, quindi `from: on → to: off` non scattava mai). Ora usa
  il **nostro `binary_sensor.<auto>_in_carica`**, sempre `on`/`off`.
- **Tasto "Ferma carica" (Wallbox)**: usava `button.wallbox_charge_stop` e ripiegava sullo switch di
  **avvio** → non fermava nulla. Ora usa **`wb_stop_switch`** (Configura → Wallbox → Stop carica).
- **Schedulazione ricarica non si salvava**: i campi tornavano ai default a ogni refresh. Ora i
  valori sono **salvati nello store** ed esposti dal nuovo sensore **`Programmazione`**; il pannello
  li **ripopola** (senza sovrascrivere quello che stai scegliendo: flag "toccato").
- **Date nelle notifiche**: `2026-09-19 19:42:09` → **`19-09-2026 19:42`**.
- **Automazioni mostrate "spente"**: la lista veniva **ricostruita** a ogni aggiornamento (stato
  transitorio/unavailable). Ora si ricostruisce solo se la lista cambia e lo stato si allinea a HA
  senza toccare il checkbox che stai cliccando.

### Controlli
- `check_status.py` **[20]** (automazioni) e **[21]** (GSE).

## 1.0.18 — Due confronti di risparmio + guida

### Il problema dei km
I km termici usano **tutto l'odometro**, le ricariche solo da quando installi l'integrazione.
Due domande diverse richiedono due risposte: le ho rese **entrambe esplicite**.

- **Base odometro automatica**: al primo avvio salvo l'odometro in `install` (store). Nessun input.
- **Nuovo confronto "da installazione"** (il più attendibile): km **dal giorno dell'installazione**
  contro **solo ricariche registrate** → entrambi da dati reali, zero stime.
- Il confronto **"da sempre"** resta e usa i **valori dichiarati** (`pre_kwh` / `pre_eur`).
- In *Risparmi* nuova card **🎯 Affidabilità del confronto** con i due numeri, km e data d'installazione.

### Configurazione
- **Modello auto come 1° campo** della schermata "L'auto": prima di nome, odometro e sensori.
  È quello che imposta la foto del veicolo e la dashboard. Spostato dentro la sezione, quindi
  ora è modificabile anche dal *Configura* successivo.
- Etichette aggiornate (IT/EN/FR): "Modello dell'auto — 1ª scelta: imposta la foto".

### Guida
- Nuova sezione **§5.2 (IT)** / **§4.2 (EN/FR)**: "Risparmi con un'auto già percorsa", con la tabella
  dei due confronti e l'esempio wallbox `8.326,4 kWh`.
- Aggiunti i due campi anche alle tabelle di configurazione delle 3 guide.

## 1.0.17 — Risparmi ridisegnati (termica vs elettrica)

### Perché "Risparmiato MESE/ANNO" era 0
Il risparmio per periodo usava `cost_meters` (i *meter live*, che restano a 0) e i km del meter.
Ora il costo delle ricariche del periodo è **somma dei record**, e i km hanno come ripiego la
somma dei viaggi di quel periodo. Vale per RadiciFuel/Risparmi mese, anno e totale.

### Pagina Risparmi — nuova
- **Tabella di confronto** "🔴 Auto termica vs 🟢 Auto elettrica" con le voci
  **Carburante / Tagliandi / Bollo**, i **totali** e la **Differenza** per riga.
- **Barre semplici** che confrontano i due totali + il risparmio in evidenza.
- **Risparmio per periodo**: mese, anno, da sempre, km percorsi, prezzo carburante.
- **Fotovoltaico**: nuovo **"Risparmiato col FV"** in **€** = kWh dal FV ×
  (costo rete casa − costo FV), più i kWh dal sole.
- Card "Come si calcola" con la formula in chiaro.

### Controlli
- `check_status.py` **[18]**: verifica la struttura del confronto e che il costo del periodo
  **non** torni a usare i meter live.

### Ricariche fatte prima dell'integrazione (risparmi corretti)
Problema: i km termici usano **tutto l'odometro**, ma le ricariche registrate partono da quando
installi l'integrazione → il risparmio risultava gonfiato.
- In *Configura → Prezzi* due nuovi campi:
  - **kWh caricati prima** (es. `8326,4`);
  - **€ già spesi in ricariche prima** (ha priorità sui kWh).
- I kWh vengono convertiti in € col prezzo casa se non indichi gli €.
- In *Risparmi* la voce appare come **"🕘 Ricariche prima (dichiarate)"** con i kWh usati, ed è
  inclusa nel totale elettrico. Differenza e barre tornano coerenti.

### Peso su Home Assistant (recorder)
- Gli attributi "archivio" (viaggi, storico giornaliero/mensile, liste ricariche, consumi/temp,
  report) finivano **nel database del recorder** a ogni aggiornamento: fino a **~750 KB per ciclo**
  (solo `ArchivioViaggi` ~650 KB con 1000 viaggi). Con polling 30 s/120 s diventano centinaia di MB.
- Ora sono esclusi dal recorder con `_unrecorded_attributes`: restano **disponibili nella UI**,
  ma **non vengono più salvati** nel DB. Nessun dato perso (l'archivio vero è in `.storage`).
- **`ArchivioViaggi` 1000 → 600 viaggi**: ~650 KB → ~390 KB per ciclo nel websocket.
- **Salvataggio su disco: ogni 5 → 15 minuti** (`persist()` non forzato). Viaggi e ricariche
  si salvano comunque **subito** (`force=True`); al massimo un crash perde i contatori di 15 min.
- `check_status.py` **[19]** blocca la regressione.

## 1.0.16 — Riordino Panoramica, ricarica manuale, selettore anno

### Panoramica (p1) — nuovo ordine
1. **Prima riga**: auto · **Comandi Renault** · **Efficienza** (con dentro anche il
   **Risparmio netto**: carburante evitato, tagliandi, bollo, NETTO).
2. **Seconda riga**: **Oggi a colpo d'occhio** + **Ultima ricarica** affiancati.
3. **Terza riga**: **Mappa** + **Km percorsi (7 giorni)**.
4. **Quarta riga**: **Automazioni attive** + **Scadenze e manutenzione** (con giorni colorati:
   rosso ≤15, giallo ≤45, verde oltre).

### Mappa
- Centrata **sull'ultima posizione** dell'auto (`focus_entity` + zoom 13, `auto_fit: false`),
  mantenendo la **traccia delle 48 ore**.
- **Riempie tutta la cella** come la card a fianco (`height:100%; min-height:260px`) e dopo il
  layout forza un `resize` così Leaflet ricentra l'auto (non più spostata verso il basso).

### Storico mensile
- **Non si riapre più da solo**: lo stato aperto/chiuso è ricordato (`_mesiOpen`), come per l'archivio.
- Nuovo **selettore anno** ("Tutti gli anni" o un anno specifico).
- Tolta la doppia freccia `▼ ▼`: il triangolo era scritto a mano e si sommava a quello nativo
  del `<details>`.

### Ricariche
- **Filtri incorporati** nello Storico ricariche (una sola card, non più due).
- Nuovo box **➕ Aggiungi ricarica manuale**: data, kWh, costo, tipo e **Descrizione** → servizio
  `add_manual_charge` (nuovo campo `descrizione`, mostrato sotto il tipo nello storico).
- Nuovo box **📊 Distribuzione ricariche**:
  - **ciambella AC vs DC** e **Casa vs Pubblica** (CSS `conic-gradient`, nessuna card HACS);
  - tile: sessioni, energia totale, durata media, **potenza di picco**, costo totale, prezzo medio.
- **AC/DC rilevato dalla potenza**: ogni sessione registra il **picco** (`potenza_max_kw`);
  oltre **22 kW** (3 fasi 32 A) è considerata **DC/fast**, altrimenti **AC**. I record vecchi
  usano la potenza media come ripiego. Controllo `check_status` **[16]**.

### Wallbox (p11)
- Nuovo box **⏱️ Stima ricarica**: tempo stimato, orario stimato, costo stimato.
- Nuovo grafico **⚡ Potenza wallbox (48 h)** con **apexcharts**: area con soglie di colore
  verde < 3000 W, giallo < 6300 W, rosso oltre. Il sensore è preso da
  **Configura → Wallbox → Potenza istantanea** (non è hardcoded).

### Extra — Consumi vs temperatura esterna
- Nuovo grafico a dispersione (apexcharts): un punto per viaggio (≥3 km) con **kWh/100km** sulla
  **temperatura esterna**, più la **linea di tendenza** (regressione lineare).
- Selettore periodo: **Settimana · Mese · Stagione (90 gg) · Tutto**.
- Ogni viaggio ora salva la **temperatura esterna** all'arrivo (`temp_est`).

## 1.0.15 — Automazioni duplicate, filtro mese, indirizzo, layout Impostazioni

### Correzioni
- **Automazione "Batteria bassa fuori casa" rimossa**: era un doppione della notifica nativa
  dell'integrazione (soglia/fascia/giorni configurabili dalla vista Automazioni). Alla prossima
  "Crea automazioni consigliate" viene cancellata; restano solo ricarica completata, avvio ricarica
  e riassunto giornaliero.
- **Indirizzo (Panoramica)**: prendeva `list[length-1]`, cioè il viaggio **più vecchio** (le liste
  sono ordinate newest-first). Ora indice `[0]` = ultimo viaggio, con via + città + paese di arrivo
  (stesse chiavi della tabella Viaggi).
- **Filtro ricariche**: aggiunto il select **Mese** (Tutti, Gennaio…Dicembre) accanto a tipo,
  periodo e anno.
- **Impostazioni**: i box **Palette**, **Notifiche** e **Automazioni** ora sono affiancati su una
  sola riga (`grid g3`).

## 1.0.14 — Ricariche: costi/energia dai record, km dall'odometro, indirizzo

### Correzioni
- **Ricariche oggi/settimana/mese/anno a 0**: energia e costo per periodo erano letti dai
  *meter live*, che si aggiornano **solo** se nel polling lo stato wallbox è esattamente
  `charging` (con contatore presente). Ora sono **sommati dai record** delle ricariche
  (fonte di verità): `data["cost"]`, `data["wb_energy"]` e la tabella **Percorrenza → Caricati**.
- **Percorrenza**: la colonna "Caricati" mostrava 0 per lo stesso motivo; ora usa i record.
- **Km oggi (64 vs 58)**: il dato veniva dai **viaggi** (che si chiudono ~20 min dopo la sosta).
  Ora ha priorità il **delta odometro giornaliero** (`sensor.<auto>_km_giornalieri`), il dato reale
  dell'auto; i viaggi restano come ripiego.
- **Indirizzo**: leggeva chiavi che non esistono sul tracker. Ora usa **via + città + paese**
  dell'ultimo viaggio (stessa fonte della pagina Viaggi), con fallback sul geocode dell'integrazione.
- **Etichetta**: "Colonnine fuori casa" → **"Colonnine"**.
- **Efficienza su mobile**: i tre valori (%batt/100km, costo/km, costo/100km) ora stanno
  **sulla stessa riga** (griglia a 3 colonne fisse), non più impilati.

### Controlli
- `check_status.py` **[15]**: fallisce se costi/energia delle ricariche tornano a usare i meter live.

## 1.0.13 — Fix pannello morto (setConfig usava _cfg prima di crearlo)

### Bug critico (regressione 1.0.11)
- `setConfig` chiamava `_startVersionWatch()` **prima** di assegnare `this._cfg`. Quella funzione
  fa `this._sid("prossima_scadenza")` → `this._slug(this._cfg.name)` su `undefined` →
  **TypeError** → `setConfig` si interrompeva e la card non veniva mai configurata:
  **pannello vuoto/bloccato**.
- Ora `this._cfg` viene assegnato per primo; `_checkVersion()` e `_startVersionWatch()` girano
  **dopo**. In più il watcher risolve l'entità **a ogni giro** (non più una volta sola all'avvio),
  così non dipende dall'ordine di inizializzazione.
- `check_status.py` **[14]**: fallisce se una chiamata precede `this._cfg = {...}` nella
  `setConfig`. Verificato che cattura davvero l'ordine rotto.

## 1.0.12 — Fix blocking call nell'event loop (dashboard rotta)

### Bug critico (regressione 1.0.11)
- La versione veniva letta con `open()` **dentro l'event loop** (chiamata da `extra_state_attributes`
  di un sensore). Home Assistant la segnala come `Detected blocking call to open ... at
  custom_components/renault_ev_center/const.py` e in pratica la piattaforma `sensor` non si
  completava più → pannello vuoto.
- Ora la versione è letta **una sola volta**, all'avvio della entry, dentro
  `hass.async_add_executor_job(...)` e salvata su `coordinator.version`. I sensori leggono un
  attributo in memoria: **zero I/O** a runtime.
- `const.py` non contiene più I/O (il check [11] ora lo verifica).

## 1.0.11 — Panoramica: batteria/media, costo ricariche, auto-refresh via websocket

### Correzioni
- **Panoramica → Ultima ricarica**: "Batteria" e "Media" erano vuoti perché il pannello cercava
  chiavi inesistenti (`soc_inizio`, `media_kw`). Il record usa `soc_start`/`soc_end` e
  `potenza_media_kw` (le stesse che la pagina Ricariche legge correttamente).
- **Costo totale ricariche a 0 €**: il totale è ora ricalcolato **anche al caricamento**
  dell'integrazione, non solo a fine ricarica — così i record già in archivio entrano subito
  nel conteggio.

### Auto-refresh — ora via websocket
- La versione dell'integrazione viaggia come **attributo del sensore "Prossima Scadenza"**
  (`version`), quindi arriva al pannello per **websocket**, senza passare da cache HTTP o
  Service Worker. Il controllo gira **ogni minuto** (prima ogni 2) + 3 s dopo l'apertura.
- Il `fetch` del file JS resta solo come ripiego per integrazioni vecchie.
- In console: `Renault EV Center: JS 1.0.11 · integrazione 1.0.11`.

## 1.0.10 — Release beta e versioning a 3 numeri

### Versioning (regole definitive)
- **Solo 3 numeri**: `x.y.z`. Il quarto numero **non si usa più**: HACS prende la *prima* release
  dell'elenco GitHub e con 4 numeri l'ordine si rompe (`1.0.6.8` prima di `1.0.6.12` → nessun
  aggiornamento). Sequenza: `1.0.10 → 1.0.11 → …`, `1.1.0` per gruppi di funzioni.
- **Versioni di test**: `VERSION = 1.0.10-beta` → il workflow crea una **pre-release GitHub**
  (`--prerelease`). HACS la mostra **solo** a chi attiva *"Mostra le beta"* su quel repository;
  per gli altri l'ultima stabile resta quella valida.
  ⚠️ Senza `--prerelease` una beta verrebbe distribuita a tutti come stabile.
- `check_status.py` [13] accetta `x.y.z` e `x.y.z-suffisso`, rifiuta i 4 numeri.

### Release
- `collapse-release.yml` accorpa **più serie** in un colpo (input `1.0.5,1.0.6` → un tag `1.0.5`).

## 1.0.9 — Auto-refresh, costo ricariche, layout Extra

### Auto-refresh (niente più Ctrl+F5)
- Il controllo versione ora gira **anche periodicamente** (ogni 2 minuti + 5 s dopo l'apertura):
  prima girava solo in `setConfig`, quindi una pagina **già aperta** durante un aggiornamento
  non se ne accorgeva mai.
- Il reload usa un **cache-bust** nell'URL (`?_recv=<versione>`) e logga in console
  `JS <mia> · integrazione <server>` per diagnosticare al volo.
- La versione arriva dalla config della card (letta dal `manifest.json`), non dal file JS:
  la cache non può più mascherare l'aggiornamento.

### Correzioni
- **Costo totale ricariche a 0**: `cost_total` è ora ricalcolato come **somma delle ricariche
  registrate** (fonte di verità), non solo accumulato dal contatore live della wallbox.
- **Extra**: "Meteo vs consumi" e "Top & Stop · mese" ora affiancati; le Note sono una card a parte.
- **Automazioni**: rimossa la card "Priorità batteria casa" (resta come `number` tra i dispositivi).
- **Versioning**: `collapse-release.yml` accorpa più serie in un colpo (`1.0.5,1.0.6`).

### Bug critico
- **Notifiche ripetute (~2000 a notte)**: `persist()` e il salvataggio allo shutdown
  sovrascrivevano `counters`, cancellando `last_notify` / `last_low_notify` / `balance_last` /
  `last_geocode`. Ora fanno **merge**: il riepilogo scadenze torna a inviarsi una sola volta al
  giorno e la card "Bilanciamento solare" non resta più vuota.
- **Riepilogo giornaliero** (21:30): aggiunti **kWh consumati** e **costo totale della giornata**
  (energia × tariffa casa) con fallback "non disponibile".
- **Consumo batteria di oggi**: riferimento = **SoC massimo della giornata** (dati app Renault),
  non più la sola somma dei viaggi (né una baseline falsata da un riavvio a metà giornata).
- **Energia di ricarica**, in ordine di affidabilità: 1) delta contatori wallbox, 2) **integrale della
  potenza istantanea** accumulato nella sessione, 3) stima dal SoC (solo fuori casa). A casa, se la
  misura manca, il record viene marcato `stima`.
- **Notifica batteria scarica**: oltre a soglia % e fascia oraria, ora si scelgono **i giorni della settimana**.
- Nuovo sensore **Δ % Ultima Carica** (`soc_end − soc_start`).
- I comandi `Avvia carica` del pannello sono dell'**auto** (app Renault); lo **stop** resta lato wallbox.

### HACS — perché non vedeva più gli aggiornamenti- HACS prende come "versione disponibile" la **prima release dell'elenco GitHub**, senza ordinarla.
  Con tag a 4 numeri (`1.0.6.8` vs `1.0.6.12`) l'ordine si rompe: GitHub metteva in testa `1.0.6.8`,
  cioè la stessa versione installata → nessun aggiornamento proposto.
- Da qui in avanti la versione è **semver a 3 numeri** (`1.0.7`, poi `1.0.8`, `1.0.9`, `1.1.0`, …).
  `check_status.py` [13] blocca versioni non `x.y.z`.

### Auto-refresh (niente più Ctrl+F5)
- La card dichiara la **versione dell'integrazione** (`version` nella config, letta dal manifest):
  il pannello la confronta con il proprio JS e ricarica la pagina **una volta** se differiscono.
  Prima il confronto rileggeva lo stesso file JS: con la cache di mezzo restava vecchio-con-vecchio
  e non scattava nulla.
- `check_status.py` [11]: fallisce se `REC_VER`/`CARD_VER` non corrispondono a `VERSION`.

### Configurazione
- **Wallbox**: mappabili in *Configura → Wallbox* sia **avvio** sia **stop** carica (switch/button).
- **Comandi**: mappabili **luci esterne** (light/switch/button) e **clacson** (button/switch).
- **Promemoria batteria bassa**: soglia % e **fascia oraria con time picker** (prima testo libero).
- Cleanup automatico delle **automazioni orfane** quando il nome dell'auto cambia (niente più
  "Programma avvio ricarica" duplicato).

### Pannello
- **Fix layout**: un `</div>` orfano in Panoramica spostava tutte le altre pagine a sinistra;
  `check_status.py` [12] ora verifica il bilanciamento dei `<div>`.
- **Avviso batteria bassa**: tornata la configurazione in *Automazioni* — attivo, soglia %,
  dalle/alle e **giorni della settimana** (nuovo servizio `set_low_soc_days`).
- Grafico Km percorsi: senza `apexcharts-card` compare **solo** l'avviso d'installazione.
- Card **"Automazioni create"** spostata in cima accanto a *Fine ricarica*, con **icona per tipo**.
- Panoramica: i KPI dell'auto sono **box cliccabili** (aprono il sensore) con **% e kWh consumati oggi**
  al posto di €/km; **Efficienza** mostra %batteria/100km al posto dei duplicati.
- Comandi: **Avvia carica** ora è il comando dell'**auto** (app Renault), **Zona ricarica** e **Indirizzo**
  (dai viaggi); il comando **stop** è lato wallbox, non Renault.
- Panoramica: **grafico Km percorsi 7 giorni** (colonne km + linea consumi) accanto al box
  **Automazioni attive**. Con `apexcharts-card` installata usa il grafico completo, altrimenti
  mostra l'avviso d'installazione.
- **Archivio viaggi**: i rami chiusi dall'utente **non si riaprono più** al refresh.
- **Dettaglio viaggi**: aggiunto il filtro **da / a** (date), oltre a anno e mese.
- Box KPI più leggibili; **Efficienza** con %batteria/100km (con ripiego calcolato se il sensore è a 0).
- Risparmio netto e costi con **2 decimali**; **mappa** con zoom predefinito più ampio.
- Rimossi i doppioni: box promemoria da *Automazioni* e la voce "Fine ricarica" duplicata.

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
