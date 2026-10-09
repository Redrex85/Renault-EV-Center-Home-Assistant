# Changelog

Release accorpate: **1.0.4 · 1.0.3 · 1.0.1 · 1.0.0** — le patch `1.0.3.x` / `1.0.4.x`
non esistono più come release separate.
La serie **1.0.5** è ancora attiva come `1.0.5.x`; verrà accorpata in un unico tag `1.0.5`
al passaggio alla **1.0.6** (workflow *Collapse release series*).

## 1.1.2 - Fix: il pannello non si apriva (chiave I18N con "×")

- **`SyntaxError: illegal character U+00D7` che impediva l'apertura della dashboard.**
  La chiave `lbl_termica_teorica_450_×_tagliandi` era scritta **senza virgolette** negli
  oggetti `I18N`: `×` non è un carattere valido per un identificatore JS, quindi l'intero
  `panel.js` non veniva parsato (nessuna pagina si apriva). Ora la chiave è quotata in
  tutte le lingue.
- **Guardia** in `tools/check_status.py`: verifica che ogni chiave `I18N` non quotata sia
  un identificatore JS valido (previene la regressione).

## 1.1.1 - Fix foto auto (modello da Opzioni + cache)

- **La foto dell'auto restava quella generica ("macchinina" 🚗).** `setup_car_image`
  leggeva il modello solo da `entry.data`; chi l'aveva scelto/cambiato dal flusso
  **«Configura»** (che scrive in `entry.options`) cadeva sul default `Custom` → foto
  generica. Ora il modello è letto da `{**entry.data, **entry.options}`.
- **Cache dell'immagine:** pannello e card ora aggiungono `?v=<versione>` alla foto,
  così dopo l'aggiornamento il browser non serve più la vecchia `auto.png`.

## 1.1.0 - Pannello multi-lingua (IT/EN/FR/ES/DE)

- **Internazionalizzazione del pannello.** Tutte le stringhe hardcoded (~230) ora
  passano da `I18N` + `_t(chiave, fallback)`: titoli (`h3_`), etichette (`lbl_`),
  opzioni, note, placeholder, tooltip, temi colore, nomi dei mesi, stati wallbox e
  messaggi toast. Lingue supportate: **IT (fallback), EN, FR, ES, DE**.
- **Selettore lingua** in *Impostazioni → card "🌐 Lingua"*; la scelta è salvata in
  `localStorage["rec_lang"]` e al cambio il pannello si ricostruisce. Lingua iniziale
  da `hass.language` (fallback IT).
- **Traduzioni lato HA:** aggiunti `translations/es.json` e `de.json` (333 foglie
  ciascuno, allineati a `en.json`/`fr.json`) → anche il config/options flow è tradotto.
- Il rendering **italiano resta identico** (fallback = testo originale).

## 1.0.55 - Carica programmata, foto auto, GSE sulla casa, potenza wallbox in sessione

- **La carica non si fermava a SoC obiettivo / fine finestra.** Il fermo nel
  coordinatore e' governato da `switch.<nome>_carica_programmata`, che nasce OFF:
  il checkbox "Attivo" del pannello salvava solo il programma e non accendeva lo
  switch, quindi l'automazione avviava ma nessuno fermava (carica fino al 100%).
  Ora il salvataggio del programma rispecchia lo switch e, all'avvio, l'integrazione
  accende il gate se il programma salvato e' attivo: basta aggiornare.
- **Foto auto mancante** per Megane/New Megane/Scenic/Twingo: i file usano il
  suffisso `_etech`, lo slug di HA produce `_e_tech`. Aggiunto il fallback del nome.
- **I campi del programma ricarica si azzeravano.** `_update()` riscriveva gli input
  dal salvataggio a ogni refresh: bastava cambiare pagina e l'ora/SoC digitati
  sparivano. Ora restano finche' non premi "Salva programma ricarica".
- **GSE: la soglia era applicata solo alla wallbox.** `_apply_gse` metteva la wallbox
  al budget pieno (es. 3 kW) senza sottrarre il resto della casa, quindi il totale
  casa sfondava la soglia. Ora la corrente e' calcolata dal margine reale, con una
  **tolleranza +10%** sul budget (`const.GSE_TOLERANCE`, 3/4.5 kW possono sforare):
  `budget*1.1 - (casa_totale - wallbox)` via `home_power_sensor` (fallback invariato
  se il sensore manca). Es.: casa 3.94 kW, wallbox 2.91 kW, budget 3 kW -> 10 A (non 13).
- **GSE: se non basta nemmeno il minimo (6 A)** la ricarica viene **fermata** (non piu'
  solo ridotta) e riprende solo se i consumi restano sotto soglia per **30 minuti**, in
  fascia impostata e sotto il SoC obiettivo (`_gse_resume_ok`). Notifiche su stop/ripresa,
  avvio con l'entita' "Avvio carica wallbox" / stop con "Stop carica wallbox".
- **Bilanciamento casa vs GSE:** con la GSE attiva `_home_balance` non tocca piu' gli
  ampere (prima li riportava a 25 A ignorando il tetto GSE di 3 kW, stesso entity).
- **Sessione corrente:** aggiunta la potenza istantanea della wallbox in **W**.

## 1.0.53 — Risparmi (regressione 1.0.52), record "Peggiore", media giornaliera

Tre correzioni:

- **Risparmi spariti con la 1.0.52.** La 1.0.52 accettava l'id col nome della card solo
  se l'entità era viva, ma poi pretendeva che l'id alternativo esistesse **come id
  completo**: le ricerche per **prefisso** (`risparmio_totale_vs` →
  `..._risparmio_totale_vs_diesel`) ricadevano sul nome della card e non trovavano più
  nulla — pagina Risparmi vuota e card *Risparmio netto* col calcolo di ripiego. Ora il
  prefisso reale viene sempre usato quando l'entità col nome della card non è viva.
- **Record "Peggiore" assurdo (37,7 kWh/100km).** Il confronto Top/Stop del mese
  accettava anche viaggi da 1-2 km con delta batteria rumoroso. Ora vale lo stesso
  filtro del record *Migliore*: almeno 3 km e consumo fra 0 e 60 kWh/100km.
- **"Km percorsi (7 giorni)" con la media a 0.** La linea *Media Consumi* era la media
  giornaliera di `sensor.<nome>_kwh_per_100km`, che vale **0** finché il dato non è
  pronto (subito dopo un reload dell'integrazione i sensori sorgente sono
  `unavailable`): bastava un campione a 0 per far crollare la media del giorno. Ora il
  sensore pubblica `unknown` invece di 0 quando il dato non è pronto, e il grafico
  esclude comunque gli 0 dalla media (`transform`).

Per cancellare un singolo viaggio dallo storico: servizio
`renault_ev_center.delete_trip` con `trip_id` = `id` del viaggio (visibile fra gli
attributi di `sensor.<nome>_viaggi_recenti` / `archivio_viaggi`, o nell'export CSV).
Serve poi ricaricare l'integrazione perché i record vengano ricalcolati.

Pannello allineato a **1.0.53**.

## 1.0.52 — Entità omonime morte: vince quella viva

Numerazione: quella che era annunciata come `1.0.51.10` esce come **1.0.52** — con
quattro numeri il confronto fra `1.0.51.9` e `1.0.51.10` ordina male (`10` prima di
`9`), quindi i tag vanno a tre cifre.

Due rifiniture sulla scia di 1.0.51.8/1.0.51.9:

- **`_car()` preferisce l'entità viva.** Anche `_car()` (device_tracker, binary_sensor,
  button, climate...) si fermava alla prima omonima **esistente**: con un orfano di una
  entry cancellata restituiva quello — un `device_tracker` senza `latitude`/`longitude`
  — e la mappa restava vuota. Ora scarta `unavailable`/`unknown`, sia tra i candidati
  sia nel ripiego sull'entità del device Renault ufficiale.
- **La mappa non riparte più da zero a ogni rientro.** La 1.0.51.9 distruggeva la card
  mappa uscendo dalla pagina: al rientro la mappa ricreava contesto WebGL e tile, e
  sembrava lenta o "non caricare". Ora la card resta montata: viene creata solo la prima
  volta che la pagina è visibile. Il riciclo dei contesti WebGL inutilizzati lo fa il
  browser.
- **La mappa riprova se il box non è ancora disegnato.** Il primo layout può arrivare
  con altezza 0: prima si usciva e la mappa non compariva più finché non si cambiava
  pagina. Ora al massimo 4 tentativi (2 secondi) e poi si ferma — nessun loop infinito.

Nessuna entità rinominata. Pannello allineato a **1.0.52**.

## 1.0.51.9 — Mappa: il contesto WebGL viene liberato

Due ritocchi alla card mappa nativa (WebGL):

- **La card mappa vive solo mentre la pagina è visibile.** Prima, una volta creata,
  restava montata anche uscendo dalla pagina: il contesto WebGL rimaneva allocato e il
  browser — che ne tiene pochi e li scarta — finiva per ucciderlo, con
  `WebGL context was lost` in console e mappa grigia. Ora `_goto()` la distrugge quando
  si cambia pagina e la ricrea al ritorno.
- **Niente mappa senza coordinate.** Se il `device_tracker` non ha ancora
  `latitude`/`longitude`, la card non viene creata (mostra "Posizione non disponibile"):
  era la causa di `Expected value to be of type string, but found null instead`.

Le due righe su `.../static/fonts/roboto/*.woff2` ("precaricata, non utilizzata") sono
del frontend di Home Assistant, non di questa integrazione.

## 1.0.51.8 — Risparmi col prefisso sbagliato, stagione vera, mappa WebGL

Cinque correzioni, tutte di pannello (nessuna entità rinominata, nessuna migrazione):

- **Risparmi vuoti o con un numero sbagliato.** Il pannello costruiva l'id dei sensori
  dal nome scritto nella card **senza controllare che l'entità fosse viva**: con una
  famiglia omonima rimasta lì (entry rimossa o rinominata) i sensori `risparmio_*` non
  venivano trovati, la card *Risparmio netto* mostrava il ripiego client
  (spesa teorica − costo ricariche: 495 € invece dei 4,60 € reali) e la pagina
  *Risparmi* restava a "—" col messaggio "Attiva il confronto con l'auto termica".
  Ora `_eid()` accetta l'id col nome della card **solo se vivo**, altrimenti passa
  alla famiglia reale eletta da `_pfx()`; `_sensorByPrefix()` preferisce l'omonimo
  vivo; `_rispNum()` ripiega sull'attributo omonimo
  (`totale`/`mese`/`anno`/`tagliandi`/`bollo`).
- **Numeri non arrotondati.** *Carburante evitato*, *+ Tagliandi* e *+ Bollo* (in
  Panoramica e in Manutenzione) non avevano `data-dec`: finivano nel ramo stringa e
  stampavano il float grezzo (`495,04600000000005`). Ora sono a 2 decimali.
- **"Consumi vs temperatura": periodi veri.** "Mese" erano *gli ultimi 31 giorni* e
  "Stagione" *gli ultimi 90*: con 12 giorni di storico le voci Mese, Stagione e Tutto
  restituivano gli stessi punti, e solo "Settimana" cambiava qualcosa. Ora
  *Settimana* = ultimi 7 giorni, *Mese* = mese di calendario, *Stagione* = stagione
  astronomica in corso (21/03, 21/06, 23/09, 21/12), *Tutto* = tutto; i punti senza
  data restano fuori dalle finestre finite.
- **Mappa: contesti WebGL a ripetizione.** La card mappa nativa (WebGL) veniva
  ricreata a **ogni** cambio di posizione GPS e, con la pagina nascosta, la funzione
  riprovava ogni 200 ms **all'infinito**: da lì i `WebGL context was lost` e le
  `Subscription not found` in console. Ora la card si crea solo quando la pagina è
  visibile (la ridisegna `_goto`), si ricentra al massimo una volta ogni 5 minuti e
  il retry infinito non esiste più.
- **README**: badge del canale Telegram ufficiale
  ([t.me/redrex_domotica](https://t.me/redrex_domotica)) nelle tre sezioni (IT/EN/FR).

Pannello allineato a **1.0.51.8** (`VERSION`, `manifest.json`, `REC_VER`, `CARD_VER`,
`preview/index.html`).

## 1.0.51.6 — Risparmio calcolato sui km tuoi, wallbox in Wh

Due correzioni:

- **Il costo termico usava l'odometro intero.** Su un'auto comprata usata (10.000 km
  già percorsi) il confronto veniva fatto su 12.000 km invece che sui 2.000 tuoi, e
  il risparmio risultava gonfiato. Ora la base è l'odometro **all'attivazione**
  (`install.odometer`: *Chilometri all'attivazione* in Configura, oppure catturato al
  primo avvio) → `km_tot = odometer − base`. Le etichette del pannello passano da
  "Km percorsi / km totali (odometro)" a "Km miei (dall'attivazione)", e i blocchi
  "Da sempre" diventano "Totale".
- **Wallbox che espone i contatori in Wh.** Sessione ed energia totale venivano lette
  come se fossero kWh: con un sensore in Wh i valori risultavano 1000× e i delta dei
  contatori inquinavano kWh e costi di ricarica. Ora il coordinatore usa `_num_kwh()`,
  che guarda `unit_of_measurement` e divide per 1000 se è "Wh"; il pannello fa lo
  stesso con `_kwhE()` per le tile *Sessione* ed *Energia totale*.

## 1.0.51.5 — Filtro ricariche che non filtrava

Un difetto:

- **Filtro ricariche che "non filtrava".** I select Tipo/Periodo/Mese/Anno **non
  entravano nella firma dell'early-exit** del coordinatore: `async_select_option()`
  chiedeva il refresh, ma `_async_update_data` usciva subito restituendo `self.data`
  e `charges_filtered` restava quello del filtro precedente — mese "Ottobre" e la
  tabella mostrava ancora Settembre. Ora `_curr_inputs` include `_filtri_sig()`.
  Verificato sul campo: su una installazione con `periodo=Tutto` + `mese=Agosto`
  uscivano **tutte** le 7 ricariche di Settembre, segno che il filtro non veniva mai
  applicato dopo il cambio del select.

## 1.0.51.4 — Risparmi a "-" con un carburante diverso dal diesel

Un difetto, segnalato da chi ha installato l'integrazione su un'altra auto:

- **Risparmi a "-" per chi non ha il diesel.** Il pannello puntava a entità fisse
  `..._risparmio_totale_vs_diesel` / `..._risp_mese_vs_diesel` / `..._bollo_vs_diesel`,
  ma i sensori si chiamano `Risparmio Totale vs <nome carburante>`: con "Benzina",
  "Gasolio" o un nome libero la stringa non combaciava e le tile mostravano "-" (le
  viste Risparmi usavano già la ricerca per prefisso, le tile no). Ora c'è un helper
  `_rispNum()` che cerca il sensore per prefisso, e `_sensorByPrefix` usa il prefisso
  reale delle entità (serve anche se l'entry è stata rinominata). Guardie aggiornate.

## 1.0.51.3 — Manutenzione invisibile, storico ricariche vuoto, bollo/tagliandi senza anni

Sei difetti: quattro sulla card Manutenzione, due su pannello (viaggi/ricariche):

- **"Intervento registrato" ma la riga non compariva.** `persist(force=True)` non
  invalidava l'early-exit: `_curr_inputs` guarda solo odometro/SoC/stato, quindi con
  l'auto ferma nulla cambiava e il record restava fuori da `maintenance["items"]`.
  Ora `persist(force)` azzera `_last_inputs` e i servizi manutenzione/scadenze
  chiedono `async_request_refresh()` → la riga appare subito, non fra 2 minuti
  (eco-poll minimo 120 s con la macchina ferma).
- **Bollo termico contato per un solo anno** (`bollo_termica = bollo_termico` = 350).
  Con acquisto 03/2023 servono 1050. Ora `anni dall'acquisto × costo annuo`, sia per
  la termica sia per l'EV.
- **Tagliandi termici calcolati sui km** (`km/15000 × 450` = 1800 con 70592 km).
  Con costo impostato a 450 € e auto di 3 anni l'atteso è 1350. Ora
  `anni × costo annuo`, con fallback al vecchio calcolo km-based se manca la data
  di acquisto. Resta invariato `teo_tagliandi` della card Manutenzione, che è la
  scadenza per intervento sull'intervallo km.
- **Etichetta "Costo tagliando termico (€)"** → **"Costo tagliando termico (€/anno)"**
  in Configura (it/en/fr + strings), con unità del selettore allineata a `€/anno`
  come già accade per il bollo.
- **Storico ricariche vuoto, sia per il mese corrente sia per il precedente.** I due
  filtri erano combinati con AND: `filtro_mese` = "Ottobre" **e** `filtro_periodo` =
  "Mese" (dal 01/10). Un mese diverso da quello in corso restava quindi **sempre**
  vuoto, e a inizio mese restava vuoto anche il mese corrente. Ora il mese scelto
  **sostituisce** la finestra del periodo, e `filtro_mese` parte da "Tutti": sono i
  pulsanti Settimana/Mese/Anno/Tutto a decidere (a inizio mese il risultato è lo
  stesso di prima).
- **Albero viaggi lunghissimo.** Il **mese precedente** ora resta chiuso di default;
  un'apertura manuale viene ricordata come prima, il resto resta aperto.

## 1.0.51.2 — Carica programmata: avviava due volte, non fermava mai, date rotte

Tre difetti trovati sulla carica notturna reale (23:05 → **100% alle 06:13**,
nessuno stop né alle 80% né alle 07:00):

- **Il fermo non partiva MAI.** Il gate era
  `if not (self.charge_sched_enabled and self._switch_on("charge_sched")): return`
  ma **`CONF_CHARGE_SCHED_ENABLED` non compare in nessuno schema del config
  flow** (solo import) → restava sempre `False` → il blocco era irraggiungibile
  anche con lo switch acceso. Ora il gate è **solo** sullo switch
  *Carica Programmata*; l'opzione morta è stata rimossa. Guardia `[63]`.
- **Avvio unico: solo l'automazione della vista Automazioni.** Il coordinatore
  premeva *Avvia* anche lui (in `orario` e in `percentuale`), così la carica
  partiva **due volte**: automazione alle 23:05 + poll nello stesso istante.
  Ora `_handle_charge_events` **ferma e basta** — `_wb_charge(True)` non esiste
  più, via anche `_sched_done_key` e `avvio_soc`. Di conseguenza il numero
  *Carica avvio sotto* non ha più effetto: è l'automazione a decidere quando
  parte. Guardia `[64]`.
- **Stop con catena di fallback.** `wb_stop_switch` → `charge_target_number`
  (porta il target al SoC attuale) → in ultimo il button di avvio: prima, senza
  stop mappato, si ripremeva l'avvio che non ferma nulla.
- **`Could not parse date at 'advanced.tagliando_data'`.** `_sugg_date`
  passava al `DateSelector` qualsiasi stringa non vuota: un valore salvato in
  un altro formato (campo testo nelle vecchie versioni) faceva fallire la
  validazione e il modulo **Configura non si apriva**. Ora `_norm_date()`
  riporta a `YYYY-MM-DD` i sei campi data (acquisto, assicurazione, tagliando,
  bollo, revisione, assicurazione2), normalizza `15/03/2027` e `2027-3-5`,
  azzera il resto con un warning in log — e lofa **anche su `base`**, sennò il
  valore vecchio restava in `entry.options` e il problema tornava. Guardia `[65]`.

## 1.0.51.1 — Shutdown: contatori, install e schedule non spariscono più

**Bug radice** trovato a audit su HA reale. `_async_save_on_stop` salvava il
file **appiattito** (`counters | {trips, …}` al top-level), mentre `async_load`
legge `raw["counters"]`, `raw["install"]`, `raw["schedule"]`: ogni shutdown
pulito lasciava un file senza quelle chiavi e al riavvio **tutti i contatori
tornavano a 0**, sparivano *Chilometri all'attivazione* e la programmazione di
ricarica.

- **Salvataggio allo shutdown con la stessa forma di `save()`** —
  `MateStore._payload()` + `save_now()`: `counters`, `install` e `schedule`
  restano annidati. Guardia `[61]`.
- **km/kWh dei periodi lunghi non scendono più sotto i viaggi.** Misurato:
  `km_settimanali/mensili/annuali = 0` e
  `energia_batteria_settimanale/mensile/annuale = 0`, mentre l'archivio viaggi
  diceva 102 / 627 / 627 km e 11,28 / 91,37 / 91,37 kWh. Solo i valori *giorno*
  sembravano OK perché lì esisteva già un fallback. Ora `_km_shown()` e
  `_kwh_shown()` prendono il **maggiore** fra meter e somma viaggi — la stessa
  "fonte di verità" già usata per costi ed energia wallbox. Esteso a risparmio
  mese/anno, CO₂, `km_anno`, report generale e `today_rec`.
- **Archivio mensile protetto.** `arch_mese[mese corrente]` veniva congelato col
  valore del meter: con il meter a 0 anche lo storico anni perdeva il mese.
- **kWh disponibili con SOH.** `battery_kwh` usava la capacità **nominale**
  (60 kWh → 21,0) mentre `kwh_per_1_batteria` usava quella **effettiva**
  (56,4 → 0,564): due entità che si contraddicevano. Guardia `[62]`.

## 1.0.51 — Rimosso "Best efficienza" (valore sballato)

Il tile prendeva il **minimo** `kwh/100km` su **tutti** i viaggi, senza filtro: un
tratto da 1-2 km o con delta batteria rumoroso batteva il record e dava
**4 kWh/100km**, impossibile per un'EV (12-20 reali).

- **Tile "Best efficienza" rimosso** dalla pagina Statistiche (era sballato per
  tutti, non solo per chi configura ora).
- Il valore resta negli attributi ma ora è **calcolato su viaggi ≥ 3 km** (stessa
  soglia del grafico *Consumi vs temperatura*) con soglia massima 40 kWh/100km.
- **"Chilometri all'attivazione" non si salvava.** `async_create_entry(data=...)`
  nello options flow **sostituisce** `entry.options`: se il form non riusava un
  campo (sezione *Auto* collapsed) la chiave spariva e al riaprire tornava a 0.
  Ora i valori già salvati vengono **preservati** (`setdefault`).
- **Risparmio falsato dalle gomme.** `tag_ev` sommava **tutti** i costi in
  *Interventi registrati*, quindi 850 € di gomme finivano nella colonna EV e
  venivano addebitati alla ricarica. Le gomme (e riparazioni/altro) le avresti
  fatte **anche con la termica**: ora nel confronto contano **solo gli
  interventi con tipo `Tagliando`**. Gli altri restano nella tabella ma fuori
  dal risparmio.
- **Riavvio di HA azzerava i contatori giornalieri.** Con l'auto ferma nessun
  input cambia, quindi l'early-exit del polling tornava indietro **senza**
  chiamare `persist()`: il file restava fermo all'ultimo salvataggio e al
  riavvio venivano ripristinati valori vecchi (% scaricata 14  11, persa da
  fermo 14  0). Ora l'early-exit persiste, l'unload dell'entry persiste (un
  reload/aggiornamento non passa per `EVENT_HOMEASSISTANT_STOP`) e il
  salvataggio allo shutdown non viene piu' silenziato da `except: pass`.

---

## 1.0.50 — Opzioni lette in tempo reale + Chilometri all'attivazione

- **Tagliandi: la colonna "termica" era troppo bassa.** Era il costo di **un**
  intervento (450) invece del **totale stimato** (`km_totali / intervallo × costo`).
  Con 45.000 km e 15.000 km d'intervallo → 3 interventi → 1.350. Il costo per
  intervento resta nella card *Manutenzione* (`teo_tagliandi`).
- **Viaggio fantasma 00:01–08:05** (0 km, 49% → 47%, Casa → Casa): creato dal fix
  precedente che salvava anche i viaggi con km=0 e solo ≥1% di batteria (standby).
  Ora salva solo se c'è l'**odometro** (km ≥ 0,5) oppure una **guida plausibile**
  senza odometro (≥5% di batteria in max 4 h). Standby = scartato.
- **Temperatura wallbox 0,0 °C**: il fallback cercava solo entità con *wallbox* e
  *temperature* nello stesso id. Nuovo campo **"Sensore temperatura wallbox"**
  nella sezione Wallbox → passa alla card come override `wallbox_temperature`.
- **`install_odo` (e ogni altra opzione) "non si salvava".** `self.opts` era copiata
  **una sola volta** in `__init__`: un valore impostato in *Configura* restava
  nell'entry ma non veniva piu' letto fino al reload dell'integrazione. Ora
  `self.opts` e' una **proprieta'** che legge `entry.data` + `entry.options` a
  ogni accesso → il valore ha effetto subito.
- **Bollo/tagliando senza calcoli.** Confermato: il prezzo inserito e' quello che
  deve apparire (236 = 236). Tolto il proporzionamento `anni = km/15000` che
  riscriveva il bollo a 211 e il tagliando a un multiplo dei km.
- **Ortografia**: **"Chilometri all'attivazione"** (it + strings; EN/FR con i
  loro termini: *Kilometres at activation*, *Kilométrage à l'activation*).
- **% di utilizzo a 2% SENZA ricarica intermedia**: la baseline
  `soc_start_oggi` e' il massimo SoC osservato **del record di oggi**, che si
  ricostruisce da zero se il record viene perso (es. riavvio): la partenza reale
  a 72% non era piu' in memoria e restava solo il valore finale (51%). Il
  consumo ora e' il **massimo** tra delta netto, `DeltaMeter("down")` e la
  percorrenza di oggi → torna il 21% reale. *(Il contatore di oggi si azzera
  comunque a mezzanotte, quindi da domani segna bene anche senza fix.)*

---

## 1.0.49 — Il viaggio non si chiudeva (due cause, entrambe risolte)

**Causa 1 — riavvio di HA.** `TripEngine.should_close()` confrontava
`time.monotonic()` con `mono_last_change`, che `restore()` riprende dallo store.
Dopo un riavvio `monotonic()` riparte da un **altro** valore (o `mono_last_change`
era un timestamp wall, se il record era di vecchio formato) → l'elapsed risultava
**negativo** → `elapsed >= timeout` mai vero → il viaggio restava aperto per sempre.
Fix: se `elapsed_min < 0` o `> 24h` (fuori scala) → ripiego sull'orologio di parete
(`time.time() - ts_last_change`).

**Causa 2 — GPS fluttuante in casa.** Il timer di chiusura viene rinfrescato da
`moved_gps` (soglia `0.0005°` ≈ 55 m), che serve a non chiudere il viaggio durante
la guida (il cloud Renault aggiorna l'odometro solo a motore spento). In casa il
GPS fluttua oltre quella soglia → `mono_last_change` si aggiornava a ogni poll →
il timeout non scadeva mai.
Fix: **chiusura per zona di partenza** — se l'auto torna nella zona da cui è
partita (≥ 5 min di viaggio) il viaggio si chiude subito.

Per chiudere subito il viaggio aperto: bottone **"Chiudi viaggio ora"** nella
pagina Viaggi del pannello.

### Fix km/kWh del viaggio (stessa release)

**Causa 3 — il viaggio veniva scartato.** `close()` rifiutava il record se
`km < 0.5` **in OR** con la durata: il cloud Renault aggiorna l'odometro solo a
motore spento, quindi i viaggi chiudevano con `km = 0` e sparivano del tutto —
niente km, niente kWh. E `self.active = False` veniva impostato **prima** dello
scarto, così il poll dopo riapriva un viaggio nuovo col seed corrente:
da qui il **9%** in dashboard (60 → 51) invece del **21%** reale (72 → 51).

- lo scarto ora è in **AND**: il viaggio conta se c'è km, **oppure** consumo di
  batteria (≥ 1%), **oppure** durata minima
- il viaggio resta **aperto** se l'odometro non si è ancora aggiornato ma c'è
  consumo: chiudere subito darebbe km = 0 e kWh = 0 (limite 6 h)
- riferimento confermato: **km = delta odometro**, **kWh = delta batteria × capacità**

---

## 1.0.49 — Fix A→E (naming, date, decimali, device Renault)

- **A — naming unificato.** `sensor.py` / `button.py` / `binary_sensor.py` usavano il
  default `"Auto"`, gli altri `"Renault"`: con `name` e `title` vuoti le entità si
  sparpagliavano su prefissi diversi. Ora tutte e 9 le piattaforme + `config_flow`
  usano lo stesso default (`"Renault"`).
- **B — `_entry_name()` non ritorna più `""`**: unique_id vuoto per più entry.
- **C — `_car()` multi-prefisso.** Prima provava solo `slugify(car)`, quindi i
  fallback puntavano a `sensor.renault_*` inesistenti. Ora prova `car`, poi
  `name`, poi la prima entità di quel dominio che **non** è dell'integrazione
  (device Renault ufficiale, es. `sensor.gy966mh_battery`).
- **D — virgola it-IT.** `_txt()` lasciava `String(v)` → `34.97` col punto.
  Decimali con la virgola, interi senza separatore migliaia (l'odometro non
  deve diventare `34.567`).
- **E — campi data come `DateSelector`.** `CONF_ASSICURAZIONE_DATA`,
  `CONF_TAGLIANDO_DATA`, `CONF_SCAD_BOLLO`, `CONF_SCAD_REVISIONE`,
  `CONF_SCAD_ASSICURAZIONE` erano `TextSelector` (incoerente con
  `CONF_PURCHASE_DATE`); ora `DateSelector` con `_sugg_date`.
- **F — wallbox: avvio/stop obbligatori.** In Pro/Enterprise sono ora `Required`
  insieme a potenza e stato: senza i comandi la pagina Wallbox non può avviare
  né fermare la ricarica. (La sezione resta assente in Base.)

---

## 1.0.49 — Valori configurati, consumo giornaliero, install_odo

- **Bollo 236 € → 211 in dashboard.** `anni = km_tot/15000` proporzionava il bollo
  ai km percorsi: il valore inserito non compariva mai. Ora il box di confronto
  mostra il **valore configurato** (bollo annuo, tagliando per intervento);
  il proporzionamento resta solo dove serve (stima anni di possesso).
- **Stessa cosa per il tagliando**: `tag_termica = tagliandi_termici × costo` →
  ora `costo per intervento`.
- **% di utilizzo scesa a 2%.** Il consumo giornaliero usava solo il delta netto
  (`SoC inizio giornata → attuale`): ricaricando in mezzo il valore crollava
  (72 → 51 → 85 ⇒ 72-85 < 0 ⇒ 0-2%). Ora è il **massimo** tra delta netto,
  `DeltaMeter("down")` e la % della percorrenza di oggi. **Da domani segna bene**
  anche senza questo fix (il contatore riparte a mezzanotte), ma con la ricarica
  intermedia restava sbagliato.
- **`install_odo` non si salvava** perché stava in *Prezzi energia* (sezione
  `collapsed`, facile da non vedere). Ora è nel menu **Auto**, etichetta
  **"Kilometri all'attivazione"** (`strings.json` + it/en/fr).

---

## 1.0.48 — slugify allineato a HA · audit naming

`dashboard.py` aveva uno `slugify` locale che **cancellava** la punteggiatura
invece di convertirla in `_`: `Clio E-Tech` → `clio_etech` mentre HA genera
`clio_e_tech` per gli `entity_id`. Consequenza: il campo `car:` della card non
trovava i fallback del device Renault, e l'`url_path` della dashboard non
combaciava con quello che ci si aspetta.

- `dashboard.py` → delega a `homeassistant.util.slugify`
- guardia `[48]` + verifica dei 4 default del nome ancora presenti

### Audit naming (aperto)
Restano **4 risoluzioni diverse del nome** quando `name` e `title` sono vuoti:
`sensor/button/binary_sensor` → `"Auto"` · `climate/number/select/switch/time/device_tracker`
→ `"Renault"` · `dashboard.entry_name()` → `"Renault"` · `config_flow._entry_name()` → `""`.
Con `name` obbligatorio nel wizard non scattano, ma vanno allineate: è il prossimo intervento.

---

## 1.0.47 — Tagliando/bollo che non si mantengono · media consumi che crolla

### I valori inseriti in Configura venivano buttati
Al salvataggio dello wizard, i campi di manutenzione venivano rimossi con
`user_input.pop(...)` **incondizionato** quando la feature era spenta. Compilavi
tagliando/bollo/scadenze, salvavi, e al prossimo save ritrovavi i default:
"non mantiene i valori".

- `_pop_vuoti()` rimuove solo ciò che è **davvero vuoto** (`None` o `""`), mai
  quello che l'utente ha scritto
- copy-paste bug: `notify_service` / `notify_days` venivano rimossi insieme ai campi
  della manutenzione (non dipendono da quella) — ora non vengono più toccati
- `tagliando_data`, `assicurazione_data`, `scad_bollo`, `scad_revisione`,
  `scad_assicurazione` sopravvivono al save

### Media consumi a 7 giorni che crolla
`eff_kwh_100 = 100 × kWh_disponibili / autonomia`. Quando i dati non bastano
(auto ferma, autonomia non aggiornata, polling che fallisce) il sensore **andava
a 0**, e con `group_by: avg` su `1day` la media di quei giorni si azzava.

- l'ultima efficienza valida resta memorizzata (`_prev_eff_*`) e viene riusata
  quando i dati mancano
- lo **schema apexcharts che già usi va bene com'è**, non va cambiato

---

## 1.0.46 — Il prefisso reale scarta le famiglie di entità morte

Raffinamento di 1.0.45: quando nel registro coesistono più famiglie di prefissi
(es. i `sensor.renault_*` rimasti orfani da un'entry cancellata, o una entry
rinominata le cui piattaforme non sono state ricaricate), `_pfx()` ora **sceglie la
famiglia con le entità vive** invece di dichiarare ambiguo tutto.

- entità `unavailable`/`unknown` non contano → se una famiglia è morta e l'altra no,
  vince quella viva
- **a parità nessun prefisso**: con 2 entry attive non si indovina, il pannello resta
  com'è e serve configurare il nome giusto

---

## 1.0.45 — Il pannello trovava i sensori solo col nome scritto nella card

La card dice `name: Renault`, ma le entità dell'integrazione si chiamano
`sensor.renault_scenic_*`. Tutti i `_sid()` costruivano l'id **solo** da
`_slug(name)` → `sensor.renault_*` → inesistente → mezza pagina a `-`
(foto 1: 325 km e 13683 km grazie agli override, ma *kWh a bordo*,
*consumata oggi*, *km/kWh*, *kWh/100km* tutti vuoti).
Scrivendo `renault_scenic` al posto di `Renault` tornava tutto (foto 2).

- `_pfx()` scopre il **prefisso reale** dal registro (`*_tagliandi` è l'ancoraggio:
  esiste sempre) e lo riusa in tutti i domini
- `_eid(dom, rest)`: prova col nome della card, se quell'id **non esiste** usa il
  prefisso reale — quindi la card torna corretta anche dopo un rinominamento
- **con più entry i candidati sono ambigui → nessun prefisso**: niente scelte a caso
- valido per `sensor`/`number`/`binary_sensor`/`switch`/`time`/`select`

**Nota:** se nel tuo HA ci sono **due entry** (es. una "Renault" e una
"Renault Scenic"), i sensori di quella vecchia restano vivi e il prefisso diventa
 ambiguo: in quel caso il fallback non scatta e la causa va risolta cancellando
l'entry obsoleta.

---

## 1.0.44 — Riassunto giornaliero: prefisso entità sbagliato nelle automazioni

Il riassunto delle 21:30 è un'automazione con **condizione**
`sensor.<prefisso>_km_giornalieri > 0.5`. Il prefisso veniva calcolato con

```python
slugify(str(self.opts.get("name", "Renault")))
```

mentre i sensori li crea `sensor.py` con `entry.data.get("name") or entry.title`.
Se la chiave `name` manca, è vuota o il default scatta, la condizione punta a un
`sensor.…` **inesistente** → `numeric_state` mai soddisfatto → **notifica mai inviata**.

Stessa radice del bug 1.0.39 (pannello vuoto con `car: renault`): il fix di allora
aveva coperto `dashboard.py` e `__init__.py`, ma non le **4 occorrenze** in
`coordinator.py` (`service_create_automations`, `_automations_apply`,
`service_set_schedule`, `async_sync_schedule_from_automation`).

- `coordinator.py` → tutte e 4 ora usano `slugify(entry_name(self.entry))`
- guardia `[41]` estesa a `coordinator.py`

---

## 1.0.43 — "Ultima ricarica" mostrava 0 € di costo

La riga **Costo · Eff.** della card *Ultima ricarica* leggeva
`sensor.…_costo_ricarica_corrente_stimato`, che vale
`needed_kwh × prezzo casa`. Appena la carica arriva al target
(`needed_pct <= 0`) il necessario è 0 → **il costo spariva e diventava 0 €**,
mentre kWh, % e potenza media continuavano a mostrare la carica appena chiusa.

Ora la card legge l'attributo `costo` del record **ultima_ricarica** (quello vero,
dai `charges`), con in coda il vecchio stimato solo se il record manca.
`data-dec="2"` → virgola italiana. Lo stimato resta dov'è servito: pagina *Ricarica*.

---

## 1.0.42 — automation.off inesistente · baseline installazione configurabile

### `set_auto_state` chiamava un servizio che non esiste
Spegnere "Aggiorna posizione" da `renault_ev_center.set_auto_state` falliva con
*"La servizia automation.off non è stata trovata"*: `service_set_auto_state` passava
lo **stato** (`on`/`off`) come nome del servizio, ma in Home Assistant si chiamano
`automation.turn_on` / `automation.turn_off`. Stesso errore in `async_restore_auto_states`?
No — quella era già corretta, l'errore era solo nel servizio.

### Configura → Prezzi energia → "Odometro all'installazione"
Il confronto **Da installazione** prendeva la baseline dal primo ciclo in cui
l'odometro leggeva > 0, senza possibilità di correggerla: se la prima lettura arrivava
dal cloud Renault in ritardo (0 o un valore sbagliato) la baseline restava sbagliata
per sempre, e un'auto **comprata usata** non poteva dichiarare da quanti km far partire
il confronto.

- `const.py` → `CONF_INSTALL_ODO`
- `config_flow.py` → campo numerico in **Prezzi energia** (`0` = come prima, automatico)
- `coordinator.py` → se valorizzato **prevale** sulla cattura automatica
- label in `strings.json` + `translations/{it,en,fr}.json`

Risponde: **sì, serve solo ai Risparmi** — `install.odometer` alimenta esclusivamente
il box "Da installazione" (e l'avviso "questo valore è gonfiato"). Non tocca efficienza,
km giornalieri, trip o stime di fine carica.

---

## 1.0.41 — Stop carica mappata · SOH ufficiale · override con fallback · dashboard orfane

### Stop carica: l'entità mappata veniva ignorata
`button.*` in Home Assistant hanno **sempre stato `unknown`**, e `_st()` scarta gli
stati `unknown`/`unavailable`. Un tasto avvio/stop **correttamente mappato** nello
wizard veniva quindi saltato e il pannello rispondeva "non mappato".

- `_cmdEnt(...cands)`: nuovo lookup dei **comandi** che ignora lo stato (i KPI invece
  restano su `_st()`), usato per `wb_start`, `wb_stop`, `charge` e `charge_stop`.

### Override: priorità ma senza cortocircuito
Da 1.0.39 le entità scelte nello wizard avevano priorità **ma sostituivano del tutto**
i fallback: se l'entità mappata spariva o veniva rinominata, il valore diventava `—`
anche se gli altri candidati c'erano ("aggiunto l'odometro, persi batteria e autonomia").
Ora l'override è il **primo candidato di una lista**, non un blocco.

### Capacità stimata ignorava il SOH ufficiale
`cap_stim` usava solo `soh_stimato` (ricavato dalle cariche). Ora prende prima il
**SOH ufficiale della concessionaria**, come già faceva `_eff_capacity()`.

### Prezzo medio €/kWh
Mostrato a **2 decimali** e **arrotondato per eccesso** (`Math.ceil`), con la virgola
decimale italiana.

### Dashboard orfana dopo il cambio nome
Rinominare l'entry cambia lo `url_path` della dashboard laterale: la vecchia restava
in sidebar e apriva il pannello senza i sensori nuovi. `dashboard.py` →
`_purge_orphans()` la rimuove (solo con una sola entry, per non farsi guerre tra
installazioni multiple).

### Wallbox: potenza e stato obbligatori
In **Pro/Enterprise** `CONF_WB_POWER` e `CONF_WB_STATE` sono ora `vol.Required`:
senza di loro la pagina Wallbox e il bilanciamento non hanno nulla da leggere.
Avvio/stop restano opzionali, non tutte le wallbox li espongono.

---

## 1.0.40 — Capacità dal modello · no entry duplicate · YAML legacy chiusi

### Capacità batteria dal modello scelto
`DEFAULT_CAPACITY = 60` veniva usata per **tutte** le auto. Ma **Renault 5 e Renault 4**
(nonché Zoe, Twingo E-Tech, Alpine A290) **non esistono in una variante da 60 kWh**:
sbagliava `kWh a bordo`, `kWh per 1%` e la **variante WLTP** scelta dal confronto.

- `const.py` → `MODEL_CAPACITY` (R5/R4/Zoe/A290 **52**, Twingo **27,5**, Megane/Scenic **60**)
- `config_flow.py` → `_capacity_for_model()`: se la capacità è ancora il default 60 e il
  modello ha una capacità nota, la usa. Chi la ha impostata a mano resta invariato.
- Lo schema la precompila già dal modello nelle Opzioni.

### Niente più entry doppia (entità con suffisso `_2`)
Il `unique_id` usava `.lower()` grezzo mentre l'`entity_id` usa `slugify()`: nomi che
differiscono per maiuscole/spazi/punteggiatura (`Renault ` vs `Renault`) passavano il
controllo, producevano **due entry** e gli `entity_id` venivano generati **uguali** →
seconda serie con `_2`, e la dashboard punta alla serie sbagliata.

Ora: `unique_id` costruito sullo **stesso slug** + pre-check su tutte le entry esistenti
(`already_configured`) confrontando il prefisso effettivo.

### Percorso YAML legacy chiuso
`dashboards/*.yaml` contiene **182 riferimenti hardcoded a `sensor.renault_`**: con un auto
diversa da "Renault" si rompe tutto (vedi caso reale: `sensor.renault_scenic_*` vs `renault_`).

Le 3 guide (IT/EN/FR) **non invitano più** a importarli: indicano il servizio
`renault_ev_center.create_dashboard`, che ricostruisce il pannello col prefisso giusto,
e segnalano i file come **legacy**.

### Controlli
- `check_status.py` **[42]**: `MODEL_CAPACITY` per modello, `_capacity_for_model()` chiamato
  in wizard **e** options, `unique_id` su slug, rifiuto entry duplicate, 3 doc senza invito
  all'import + con `create_dashboard` e avviso legacy → **127 controlli**.

## 1.0.39 — Dashboard e entità finalmente con lo stesso nome

### Bug: pannello vuoto con sensori popolati
Un utente aveva **~100 entità tutte funzionanti** e la **Panoramica completamente vuota**
(compresi i tagliandi inseriti a mano). Causa: **due fallback diversi per lo stesso campo**.

```python
# sensor.py (+ altre 8 piattaforme) → entità
name = str(entry.data.get("name") or entry.title or "Auto")   # → "Renault Scenic"

# __init__.py → dashboard
str(opts.get(CONF_NAME, "Renault"))                            # → "Renault"
```

Quando `entry.data` **non contiene la chiave `name`**, le entità nascono come
`sensor.renault_scenic_*` mentre la card riceve `name: Renault` e cerca
`sensor.renault_*` → **zero match, tutto `—`**.

- **`dashboard.py` → `entry_name(entry)`**: unico punto che risolve il nome
  (`entry.data` → `entry.title` → default), **stessa espressione delle piattaforme**.
- **`__init__.py`**: le 3 chiamate (`setup` / `create_dashboard` / `remove_entry`)
  usano `entry_name()`; rimosso `opts.get(CONF_NAME, "Renault")`.

### Bug: batteria/range/odometro sempre vuoti con device Renault diverso
Il wizard raccoglie `battery_level_entity`, `range_entity`, `odometer_entity`,
`charging_entity`… ma **`dashboard.py` non li inoltrava mai in `overrides`**, mentre
il pannello li legge (`_ov("battery"|"range"|"odometer"|"charging")`).

Risultato: cadeva sui fallback `_car()` che presumono `sensor.<nome_entry>_battery_level`,
ma il device dell'integrazione Renault ufficiale può chiamarsi diversamente
(es. **`gy966mh`** vs entry `Renault`) → batteria/range/odometro vuoti.

Ora le 4 entità scelte in wizard arrivano in `overrides` e il pannello le usa **prima** dei fallback.

### Fix collaterale
`async_remove_entry`: la riga `await async_remove_dashboard(...)` era stata
commentata da un edit precedente → la dashboard non veniva più rimossa
all'eliminazione dell'integrazione. Ripristinata.

### Controlli
- `check_status.py` **[41]**: `entry_name()` unico, nessun `opts.get(CONF_NAME)`
  in `__init__.py`, testa `data → title` nelle 9 piattaforme, 4 override forwardati
  → **126 controlli**.

## 1.0.38 — README trilingue completo + riga Extra a 3 card

### Pagina Extra
- **Vampire drain**, **Costo ricarica · mese** e **Prezzo medio €/kWh** tornano **tre card
  separate su un'unica riga** (`.g3`): prima il costo e il prezzo erano fusi in un box.
- Layout: `Top & Stop` (con dentro il range) / `Consumi vs temperatura` / `Consumi per
  fascia` / `Trend mensile` / `Efficienza per zona` / **riga g3: drain · costo · prezzo** /
  `Risparmio vs termica` / `Orario di partenza`.

### README trilingue
- **Sezione inglese riscritta per intero**: prima erano ~60 righe e rimandava "vedi la
  sezione italiana"; ora copre **tutto** l'italiano — Requisiti (+ i 2 avvisi ⚠️ zona Casa
  e "servono km"), Installazione (con avviso doppio riavvio), Configurazione 4 schermate
  con le 3 tabelle, **Cosa crea** (90+ entità), **Dashboard incluse** (11 viste), **Servizi**
  (tutti gli 8), **FAQ** (tutte le 8) e Crediti.
- **Sezione francese completata**: aggiunti i **2 avvisi ⚠️**, l'**avviso doppio riavvio**,
  le voci mancanti di "C'est quoi" (lista ricariche, vista mobile, viaggi verificati,
  pagina Extra, cronologia posizione), **Ce que ça crée**, **Tableaux de bord inclus**,
  **4 servizi** mancanti (`create_dashboard`, `create_automations`, `add_maintenance`,
  `renew_insurance`, `set_scadenza`, `set_tagliando`) e **3 FAQ**.

### Controlli
- `check_status.py` **[40]** → **layout 3 card su riga g3** + **parità EN/FR del README**
  (controlla gli heading e le stringhe chiave di entrambe le sezioni) → **125 controlli**.

## 1.0.37 — Ricariche verificate + pagina Extra accorpata

### Ricariche: controllo spina e wallbox di un'altra auto
- **Bug**: `CONF_PLUG_ENTITY` veniva letto ma **mai usato** → nessuna verifica che la
  corrente della wallbox fosse della *nostra* Renault.
- Ora l'energia della wallbox è attribuita all'auto **solo con la spina collegata**:
  una wallbox condivisa che carica un'altra macchina **non viene più conteggiata**
  (né kWh né €). Vincolo applicato in **3 punti**: meter, accumulo costo, sessione.
- `plug_ok` è **peggiorativo**: se la spina si stacca a metà sessione, alla fine si
  scarta la misura wallbox e si ricade sul delta SoC.
- Entità spina non configurata → nessun vincolo (compatibilità con l'installazione
  di prima).

### Fix del "13 kWh → 4,67 kWh"
- **Causa**: `counter_start` preso all'avvio sessione HA + `_best_measured_delta`
  che scarta i delta negativi (reset contatore a metà sessione) → misura a 0 →
  fallback sul **delta SoC** (4,67 ≈ 8% × 58 kWh).
- Ora la sessione accumula il delta wallbox **passo-passo** (`wb_accum`, 0 < Δ ≤ 10 kWh
  per poll): immune a reset e ad avvii in ritardo. In finalize si prende
  `max(kwh_accum, wb_accum)`.

### Pagina Extra accorpata
- **Range reale vs dichiarato** è ora dentro il box **🏆 Top & Stop · mese**
  (eliminata la card autonoma).
- **Costo ricarica per mese** + **€/kWh per mese** → un solo box **💶 Costo ricarica ·
  mese** con i due grafici impilati (dicono pressoché la stessa cosa).

### Guida
- **README + guide installazione (IT/EN/FR)**: avviso **Fortemente consigliato** —
  definire in HA **almeno la zona Casa** (altrimenti le ricariche non si distinguono
  dalle pubbliche e i prezzi casa non si applicano) e nota che **alcuni valori si
  popolano solo guidando qualche decina di km**.

### Controlli
- `check_status.py` **[39]** spina/wallbox · **[40]** layout Extra + README → **125 controlli**.

## 1.0.36 — Range: WLTP casa madre + box affiancato

### Fix
- **Range reale vs dichiarato**: il "Dichiarato" usava `sensor.autonomia_della_batteria`
  (autonomia **residua** all'attuale SoC, es. 161 km al 40%) → appariva troppo basso.
  Ora usa il **WLTP ufficiale a 100% batteria** del modello selezionato in wizard.
- **Reale** ora usa la **media di tutti i viaggi** (`efficienza_media` di `stats_all`),
  non più il sensore live dell'ultimo tratto.

### Tabella WLTP (km a 100% batteria, varianti per capacità)
| Modello | WLTP km |
|---|---|
| Megane E-Tech | 40→310 · 60→**470** |
| New Megane E-Tech | 67→**501** |
| Scenic E-Tech | 60→400 · 87→**625** |
| Renault 5 | 40→300 · 52→**400** |
| Renault 4 | 40→322 · 52→**409** |
| Zoe | 41→300 · 52→**395** |
| Twingo E-Tech | 27,5→**263** |
| Alpine A290 | 52→**380** |

Sceglie la variante batteria più vicina alla capacità configurata. Modello `Custom`
→ fallback sul sensore di autonomia residua.

### Box affiancato
- **Sinistra** = *Reale · media viaggi* (con kWh/100km e capacità sotto).
- **Destra** = *Dichiarato · WLTP* (casa madre al 100%).

### Altre correzioni pagina Extra
- **Efficienza per zona**: media **pesata per km** (`sum(e×km)÷sum(km)`); prima era
  divisa per il numero di viaggi → valori gonfiati (309, 346, 408…). Nomi zona
  `home`/`not_home` normalizzati in **Casa**/**Fuori**.
- **Orario di partenza**: conteggi senza decimali (`dec: 0`).

### Controlli
- `check_status.py` **[38]** — guardia tabella WLTP, attributo `wltp_km`, media
  e ordine del box (sinistra reale, destra dichiarato) → **123 controlli**.

## 1.0.35 — Pagina Extra: 8 grafici

> Include anche **1.0.28 → 1.0.34** (mai pubblicate separatamente).

### Nuova funzione
- **Pagina Extra → 8 nuovi grafici** (SVG nativi, con tooltip):
  1. **📈 Trend mensile kWh/100km** — media per mese: migliora o peggiora?
  2. **📍 Efficienza per zona** — kWh/100km medi per zona d'arrivo (dove consumi di più)
  3. **🔋 Vampire drain (7 gg)** — % batteria persa da fermo, giorno per giorno
  4. **💶 Costo ricarica per mese** — € spesi mese per mese
  5. **€/kWh per mese** — prezzo medio di ogni kWh ricaricato
  6. **💰 Risparmio vs termica** — termica vs elettrica vs netto
  7. **🕐 Orario di partenza** — a che ora parti di più
  8. **🧭 Range reale vs dichiarato** — autonomia reale vs costruttore
- **📍 Cronologia posizione** (Panoramica): timeline dei cambi di zona (In casa / Lavoro / Non
  disponibile) con orario — stile cronologia Home Assistant ma dentro una card del pannello.
  Registrata dal coordinator e salvata nello store.
- Il **drain giornaliero** ora viene salvato nello storico (serve per il grafico 3).

### Correzioni
- **Pagina Extra → Consumi vs temperatura**: ora **2 grafici affiancati** (`grid g2`):
  1. **Scatter colorato** (freddo = blu, caldo = rosso) con tendenza e **tooltip** sui punti;
  2. **Barre per fascia** (4 fasce: **0–10 · 10–18 · 18–26 · ≥26 °C**) con **tooltip**.
  SVG ridotto (560×150, ~metà dell'altezza precedente) — come `preview/v3.html`.
  Selettore periodo (Settimana/Mese/Stagione/Tutto) applicato a **entrambi**.
  Niente più dipendenza da `apexcharts-card` per questi due grafici.
- **"Programma clima" sembrava attivo dopo l'update**: lo switch *Attivo* aveva `checked` fisso nel
  markup e, se lo scheduler non esisteva, non veniva sovrascritto → appariva sempre acceso. Ora lo
  switch viene **sempre** impostato dallo store (`false` se lo scheduler non c'è).

### Correzioni
- **Automazioni che si riattivano** (es. *Programma clima*) su F5 / riavvio / update: ora lo **store è la
  fonte di verità** — l'integrazione **impone** a ogni ciclo lo stato on/off scelto. Il toggle del
  pannello chiama il nuovo servizio `renault_ev_center.set_auto_state` (salva + applica), quindi la tua
  scelta **non viene più sovrascritta** da HA.

### Guida
- **README**: sezione **Anteprima** con gli screenshot reali (3 per rigo, cliccabili).

### Correzioni
- **Programma clima che si riattiva**: lo stato on/off delle automazioni viene ripristinato **solo
  dopo che sono caricate** (prima il ripristino poteva girare a vuoto e poi sovrascrivere con «on»).
- **Grafico «Consumi vs temperatura» — "Errore di configurazione"**: apexcharts-card accetta solo
  `line`/`area`/`column` in `series.type` (non `scatter`); per i punti si usa `chart_type: scatter`.
  Corretto (+ `entity` sulla serie *Tendenza*).
- **«Best efficienza» sempre 0,0**: leggeva `efficienza_best`/`best`/`record`, ma il sensore espone
  `migliore_efficienza`. Corretto.
- **Aggiorna posizione auto (forzato)**: nuovo tasto in *Panoramica* (sopra la mappa) + servizio
  `renault_ev_center.refresh_car` — chiede a HA di rileggere dal cloud Renault posizione, odometro,
  batteria, autonomia, spina e stato carica (il cloud a volte resta indietro).
  In più l'automazione **«Aggiorna posizione auto»** (ogni 30 min), **attivabile/disattivabile** dalla
  vista *Automazioni*.
- **Configurazione — errori di validazione risolti**: *Contatore di casa* aveva default `"6.0"` mentre le
  opzioni sono `"3" · "4.5" · "6" · "10"` (`value must be one of…`); *Data acquisto* passava un
  `suggested_value` vuoto al `DateSelector` (`Could not parse date`). Ora i default sono validi.
- **% batt./100 km coerente col kWh/100 km**: era il delta SoC ÷ km (gonfiato sui tragitti corti, es. 60%);
  ora è **consumo (kWh/100km) ÷ capacità effettiva** → es. ~29% con 16 kWh/100km.
- **Batteria solo senza sole** (switch in *Wallbox → Bilanciamento fotovoltaico*): con lo switch ON, di
  giorno l'auto va a **solare puro** e la **batteria di casa** entra nel surplus **solo quando la rete
  importa** (sera/notte) — così non scarichi la batteria quando c'è il sole.
- **Grafico Potenza wallbox a 48 h**.
- **Lista automazioni**: le automazioni legacy rimosse (rimaste `unavailable` nel registro) **non
  compaiono più** nel pannello.
- **Wallbox condivisa con altre auto**: la *Sessione corrente* mostra i valori **solo se QUESTA auto è
  collegata/in carica** (sensore spina o stato carica). Se la wallbox carica un'altra auto, i valori
  restano «—» e non inquinano i record dell'integrazione.

### Guida
- Nuova sezione **«Caricare l'auto dalla batteria di casa (di notte)»** con il bilanciamento.

## 1.0.27 — Pagina Wallbox + automazioni

> Include anche **1.0.26** (mai pubblicata separatamente).

### Correzioni
- **Conflitto `CSS.escape is not a function`** con altre card (es. *entity-progress-card*): il pannello
  dichiarava `const CSS` a livello globale, **ombreggiando `window.CSS`** per tutte le card. Rinominato
  in `REC_CSS`.
- **Wallbox**: riga unica **Stato wallbox · Sessione corrente · Stima ricarica** (3 colonne) con
  l'**immagine della wallbox** (`wallbox.png`) più grande dentro *Stato wallbox*.
- **Corrente di carica** inglobata nel box **Sessione corrente** (slider + Applica).
- **I 3 bilanciamenti** (*Bilanciamento casa · Sperimentazione GSE · Bilanciamento fotovoltaico*) su
  **un solo rigo** (griglia a 3 colonne).
- **Stato on/off delle automazioni persistente**: quelle spente (es. *Programma clima*) **restano
  spente** anche dopo update/riavvio (salvate nello store e riapplicate all'avvio).
- **Rimozione legacy robusta** (match su id **e** alias): «Promemoria collegamento» e «Batteria bassa
  fuori casa» vengono eliminate da `automations.yaml` all'avvio.

## 1.0.25.1 — Logo, consumi, programmazione e temperatura

> Include le patch **1.0.24.1 · 1.0.24.2 · 1.0.24.3 · 1.0.24.4 · 1.0.25** (mai pubblicate separatamente).

### Correzioni
- **Sidebar**: sostituita la 🚗 con il **logo Renault EV Center** (marchio a diamante con il giallo
  Renault), adattivo al tema (`currentColor`).
- **Consumi dal SoC reale**: «Consumata oggi %», «Batteria % per 100 km» e i kWh dei viaggi ora
  derivano dal **delta SoC della batteria** (il dato effettivo), con la **capacità effettiva**
  (nominale × SOH, es. 60 × 0,94 = 56,4 kWh → **1% = 0,564 kWh**). Il calcolo dai kWh dei viaggi era
  impreciso sui tragitti corti (media non significativa).
- **Ricariche a cavallo di mezzanotte**: attribuite al **giorno di fine** (es. 23:06→00:12 conta sul
  giorno dopo), così «Ricariche oggi» le include.
- **% caricata oggi**: usava un sensore inesistente → mostrava «—». Ora usa `batteria_caricata_oggi`.
- **SoC della programmazione ricarica**: il recupero dall'automazione ora legge anche il **SoC
  obiettivo** dall'azione (`number.set_value`), non solo l'orario → non torna più a 0.
- **Temperatura esterna**: se il sensore mappato manca o è `unknown`, ripiega sull'entità **weather**
  (`weather.forecast_casa`, attributo `temperature`) — meglio di niente. Il selettore in *Configura*
  ora accetta anche entità `weather`.

## 1.0.24.3 — Ritocchi

### Correzioni
- **Prezzo carburante con 2 decimali** (es. `2,00 €/l`): in *Risparmi* era mostrato con 3 decimali.
- **Tasto "Registra ricarica" più corto**: la classe `.btn` ha `flex:1` e lo allargava a tutta la riga;
  ora è `flex:0 0 auto` (larghezza del testo).
- **Mappa a 48 ore + zoom fisso sull'ultima posizione**: ripristinata la traccia `hours_to_show: 48`,
  centrata sull'auto (la card si ricrea quando l'auto si sposta).
- **Automazioni che si riaccendevano** (es. *Programma clima*): `automation.reload` riaccendeva **tutte**
  le automazioni, non solo quelle salvate. Ora lo stato on/off di **ogni** automazione è ripristinato
  dopo il reload → restano spente se le hai spente.
- **Rimossa l'automazione duplicata "Batteria bassa fuori casa"**: la notifica batteria bassa è **nativa**;
  all'avvio l'integrazione rimuove le automazioni legacy (e riscrive `automations.yaml` anche quando
  rimuove solo quelle).
- **Doppio interruttore "Avviso batteria bassa"** nella vista *Automazioni*: rimosso quello in alto
  (resta nel box dedicato).

## 1.0.24.2 — Configurazione in una schermata + mappa

### Correzioni
- **SOH stimato mai sopra il 100%**: la stima ora richiede una **ricarica significativa (≥15%)**
  (sotto, il rapporto kWh/% è troppo sensibile e dava valori assurdi tipo 102,1%) ed è **limitata a 100%**
  anche in lettura.
- **Orario «Programma ricarica» che tornava alle 23:30**: all'avvio l'integrazione **riprende l'orario
  dall'automazione** esistente (`automations.yaml`) e lo salva nello store → **non si perde più** agli
  aggiornamenti/riavvii.
- **Carica programmata rimossa dalla configurazione**: niente più sezione nel wizard né nelle *Opzioni*;
  si usa **solo** quella nella vista *Automazioni*. Il *Target di carica* Renault è passato in *Comandi Renault*.
- **Profilo Base**: **niente sezione Wallbox** (né Bilanciamento casa / GSE) nel wizard e **niente pagina
  Wallbox** nel pannello/dashboard (già nascosta quando `wallbox=false`).
- **Configurazione iniziale in UNA schermata** (come le *Opzioni*): il wizard non è più a passi
  (auto → wallbox → impostazioni), ma mostra **tutte le sezioni** insieme — *L'auto, Comandi Renault,
  Wallbox, Bilanciamento casa, Sperimentazione GSE, Fotovoltaico* (dal profilo) *+ Batteria, Prezzi,
  Confronto carburante, Manutenzione e bollo, Notifiche, Avanzate*.
- **Sezioni chiuse di default**: tutte `collapsed`, si aprono a mano come nella schermata *Opzioni*.
- **Mappa**: niente più traccia 48 h che spostava l'inquadratura. Ora mostra la **posizione corrente**
  e la card viene **ricreata quando l'auto si sposta** → centrata sull'ultima posizione.

## 1.0.24.1 — Fix automazioni, filtri e mappa

### Correzioni
- **Tile di *Ricariche* sempre a "—" (bug)**: il loop della *percorrenza* selezionava **tutti** gli
  elementi `data-per`, comprese le tile OGGI/SETTIMANA/MESE/ANNO che usano `data-per` per il filtro,
  e le **svuotava** scrivendo "—". Ora il selettore è ristretto alle celle nel formato `periodo|chiave`
  (`[data-per*="|"]`). Valori di nuovo visibili e formattati (es. *57,84 kWh · 14,46 €*).
- **Configurazione: sezioni sempre visibili**. Tutte le sezioni del wizard (Batteria, Prezzi,
  Carburante, Manutenzione, Notifiche, Programmazione, Avanzate e, per pro/enterprise, Wallbox,
  Bilanciamento casa, GSE, Fotovoltaico) ora sono **espanse**: prima erano `collapsed` e in HA
  apparivano come intestazioni chiuse, facendo sembrare "mancanti" i menu.
- **Automazione ricarica che tornava alle 23:30**: gli orari/SoC **non si configurano più nel
  wizard**; lo scheduler nativo usa l'orario dell'**automazione salvata** (vista Automazioni) con
  priorità sui default. Prima il default `23:30` sovrascriveva la scelta dell'utente.
- **Toggle automazioni**: al **reload/aggiornamento** le automazioni **conservano** lo stato scelto
  (on/off). Solo quelle **nuove** vengono accese; quelle spente dall'utente restano spente.
- **Storico ricariche**: il filtro **mese** parte dal **mese corrente** (es. *Settembre*), senza
  ripristinare il vecchio valore.
- **Bilanciamento solare**: ora ha lo **switch on/off** (come il bilanciamento casa) al posto del
  pulsante testuale.
- **Mappa**: attende che il riquadro abbia la sua altezza prima di creare la card (Leaflet centrava
  male a 0 px) e mantiene la card viva per aggiornare la posizione.

## 1.0.24 — Profili di installazione (base / pro / enterprise)

### Nuova funzione: bilanciamento casa (contatore)
L'integrazione ora **bilanciamento anche il contatore di casa**, senza automazioni YAML. Nella
pagina **Wallbox**, accanto a *Bilanciamento solare*:
- **switch** *Bilanciamento Casa* (`switch.<nome>_bilanciamento_casa`);
- **consumo casa** live, **soglia contatore** e **ampere wallbox** attuali.

Configurazione (*Configura → Bilanciamento casa*): **sensore consumo casa** (W o kW), **contatore**
(3 · 4.5 · 6 · 10 = superiore, kW), **ampere a carico basso** (ripristino) e **ampere a carico alto** (riduzione).
Soglie derivate: alta = potenza contatore, bassa = **80%**. Isteresi: **10 min** sopra → ampere ridotti;
**15 min** sotto → ampere ripristinati (adattato dalle automazioni dell'utente).

### Nuova funzione: profilo scelto all'inizio
La **prima schermata** della configurazione ora chiede il **profilo**, che decide quali sezioni
vedrai e quali pagine compaiono nel pannello:

| Profilo | Include | Esclude |
|---|---|---|
| **Base** — solo auto | auto, viaggi, costi, ricariche, risparmi, manutenzione | **wallbox** e **fotovoltaico**; la **pagina Wallbox non compare** |
| **Pro** — auto + wallbox | Base **+ wallbox** (+ GSE) | fotovoltaico |
| **Enterprise** — tutto | Pro **+ fotovoltaico** e bilanciamento solare | — |

- Il wizard diventa: **profilo → auto → wallbox (saltata in Base) → impostazioni**.
- Le sezioni **GSE** (pro/enterprise) e **fotovoltaico** (solo enterprise) compaiono solo dove serve.
- Il profilo forza `wallbox_enabled` e `has_pv`; il pannello riceve `wallbox`/`profile` e **nasconde
  la pagina Wallbox** (sidebar, nav mobile e sezione) quando è disattivata.
- Etichette tradotte in IT/EN/FR (`selector.profile`).

### Automazione carica
- **Diagnostica**: se l'automazione del programma ricarica non ha **nessuna azione** (nessuna entità
  di avvio mappata) ora lo scrive **nel log** con la spiegazione.
- **Fallback** sui nomi comuni (`button.wallbox_charger_start`, `button.<auto>_start_charge`).
- Dopo il salvataggio l'automazione viene **accesa** se era spenta (prima restava off → non partiva),
  e se l'entità non esiste lo segnala (indizio: `automations.yaml` non incluso in `configuration.yaml`).

### Correzioni
- **Risparmi con i valori dichiarati**: `kWh/€ caricati prima` ora entrano anche nei **totali
  ufficiali** (`elettrico_totale`, `savings["totale"]` → sensore `Risparmio Totale vs Diesel` e card
  *Risparmio netto* in Panoramica), non solo nel box di confronto. Prima i due numeri non coincidevano.
- **Dettaglio viaggi recenti**: i filtri partono sul **mese corrente** (anno corrente se presente nei dati).
- **Tasto "Registra ricarica"** più piccolo (padding 8/14, font 13).
- **Mappa = stessa altezza del grafico a fianco**: riga a `grid-auto-rows:330px` e `.mapbox`
  in `height:100%` (prima era fissa a 280 px → più bassa della card Km percorsi).
- **Scadenze: km mancanti**. Le voci per chilometraggio (es. **Cambio gomme**) ora mostrano i
  **km che mancano** (`35.806 km`) invece dei soli giorni, sia nel box in *Panoramica* sia nella
  tabella in *Extra* (colonna rinominata **"Km / Giorni"**). Le voci per data restano in giorni.

### Guida
- **§1 (IT/EN/FR)**: flusso HACS completo — *repo → cerca in HACS → scarica → riavvia → aggiungi
  l'integrazione → configura*.
- **§2**: nuova **Schermata 0 — Profilo** con la tabella delle 3 opzioni e cosa comportano.
- **Risparmi (§5.2 IT / §4.2 EN/FR)**: spiegato che inserendo **kWh/€ caricati prima** i valori
  entrano in **tutti** i numeri della pagina (tabella, differenze, NETTO, barre, sensore Risparmio
  Totale e card in Panoramica) — non solo nel box "Affidabilità del confronto".

## 1.0.23 — Fonte unica prezzo carburante, orario programma, tile

### Duplicazioni eliminate (segnalate dall'utente, confermate)
- **Prezzo carburante — DUE fonti diverse** 😱
  - il **coordinator** (risparmi) usava il valore fisso di *Configura* (`fuel_price`, default 1,65);
  - il **pannello** (spesa teorica, €/km) usava `localStorage.rec_diesel` (default 1,72).
  → con 2,10 impostati in Impostazioni, i Risparmi calcolavano con **l'altro** prezzo.
  **Ora c'è una fonte unica**: nuovo `number.<auto>_prezzo_carburante`, usato da **entrambi**.
  Il campo *Impostazioni → Prezzo carburante* scrive lì (non più in localStorage).
- **Orario "Programma ricarica"**: il sensore `Programmazione` leggeva i dati del coordinator,
  che si aggiornano **solo al poll successivo** → dopo il salvataggio il form si **resettava a 23:30**.
  Ora legge **direttamente dallo store**: sempre aggiornato.

### Correzioni
- **Tile Ricariche (OGGI/SETTIMANA/MESE/ANNO)**: avevo tolto lo stile della colonna → sembravano
  spariti. Ripristinato il layout **e** resi cliccabili (filtro periodo).

### Controlli
- `check_status.py` **[22]** esteso: prezzo carburante a fonte unica, Programmazione dallo store.

## 1.0.22 — Una sola notifica, orario programmato, tile cliccabili

### Correzioni
- **Due notifiche di fine carica** → ora **una sola**: la mandava sia l'integrazione (nativa) sia
  l'automazione. Tenuta l'**automazione** "Ricarica completata" (visibile e attivabile dal pannello)
  e **aggiunta la posizione** al messaggio: `📍 <zona>`.
  La ricarica ora salva la **zona** (attributo `zona` di *Ultima Ricarica*).
- **Panoramica → "Carica programmata"** mostrava sempre `23:30` (il default dell'entità time). Ora
  legge l'**orario della programmazione salvata** (quella dell'automazione).
- **Programmazione che non si salvava**: le caselle **"Attivo"** partivano **non spuntate**, quindi il
  primo "Salva" inviava `attivo=false` e **cancellava** l'automazione. Ora partono **spuntate** e i
  campi si ripopolano dai valori salvati.
- **Ricariche**: i riquadri **OGGI / SETTIMANA / MESE / ANNO** sono ora **cliccabili** e impostano il
  filtro periodo.
- **Avviso batteria bassa**: aggiunto **lo stesso interruttore** anche nel box *Notifiche* (prima c'era
  solo nel box in basso): accendendolo in uno si accende nell'altro — è la stessa entità.

### Risposta: quale delle due automazioni serve?
- **"Avviso batteria bassa"** (notifica nativa): è quella che serve — soglia, orari e giorni
  configurabili, interruttore `switch.<auto>_promemoria_batteria_bassa`.
- **"Batteria bassa fuori casa"** (automazione): **rimossa**, era un doppione. Non c'è più nulla da
  scegliere.

## 1.0.21 — Cambio gomme: km dell'ultimo cambio

### Correzione
- Il campo della scadenza gomme era interpretato come **km obiettivo assoluto**. Ora è il **km
  dell'ultimo cambio**: l'integrazione **somma l'intervallo gomme** configurato e mostra dove
  cambiarle.
  - Esempio: ultimo cambio **60.000 km** + intervallo **40.000 km** → **"Cambio gomme · a 100.000 km"**
    con i km mancanti rispetto all'odometro.
  - Vale anche per un intervento registrato nel registro manutenzione (usa il suo km).
  - Il **Tagliando** resta invariato (lì il valore è già l'obiettivo).
- **Pannello → Manutenzione → Cambio gomme**: campo rinominato **"Ultimo cambio (km)"**, aggiunta la
  riga **"Prossimo cambio"** (km obiettivo + km mancanti) e i campi si **ripopolano** dai valori salvati.
- `check_status.py` **[22]** esteso: somma dell'intervallo all'ultimo cambio.

## 1.0.20 — Stop carica al SoC e grafico wallbox

### Correzioni
- **La carica non si fermava al SoC impostato (70%)**: due cause.
  1. In modalità **orario** lo stop avveniva **solo uscendo dalla fascia**: il SoC obiettivo era
     **ignorato**. Ora ferma anche quando `battery >= target` (il SoC dell'automazione, es. 70%).
  2. Il coordinator **non usava mai** l'entità di **stop** dedicata: se l'avvio è un `button`,
     ripremerlo **riavvia** invece di fermare. Ora per fermare usa **`wb_stop_switch`**; se manca,
     ripiega sull'avvio (switch → `turn_off`) e solo alla fine sul number target Renault.
- **Grafico apex wallbox senza valori**: il sensore può essere in **kW** (la pagina lo convertiva,
  il grafico no) e l'asse aveva un **massimo fisso 7000**. Ora se il sensore è in kW applica
  `return x * 1000` e **non c'è più il massimo fisso** (non taglia wallbox diverse).
- Controllo `check_status.py` **[22]** esteso: stop dedicato, SoC obiettivo, conversione kW.

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

### Correzioni (wallbox, stima, scadenze)
- **Automazione "Batteria bassa fuori casa" eliminata** in automatico: era un doppione della
  notifica **nativa** (quella configurabile in *Automazioni → Avviso batteria bassa*). Non serve più
  ri-lanciare "Crea automazioni": viene rimossa al primo giro.
  → **"Promemoria collegamento" NON fa la stessa cosa**: quello avvisa a un **orario** fisso di
  collegare la spina; "batteria bassa" avvisa **quando il SoC scende sotto la soglia**.
- **Stima ricarica**: usava l'*Obiettivo Ricarica* di configurazione invece del **SoC dell'automazione**
  (es. 70%): due valori diversi. Ora se la carica programmata è attiva usa **il suo SoC**.
- **Scadenze**: "Tagliando" (per km) + "Tagliando annuale (consegna)" erano **due voci** per la stessa
  cosa, con la prima a 0 giorni. Ora resta **solo quella della consegna**.
- **Wallbox**: corrente/tensione/temperatura erano lette solo da `sensor.wallbox_*` (vuote se i nomi
  differiscono). Ora c'è anche la **ricerca per nome** (`wallbox` + `current`/`voltage`/`temperature`).
- **Slider corrente**: il valore non veniva mostrato dopo un refresh (restava "—"). Ora mostra gli
  ampere correnti e non ruba il cursore mentre lo trascini.
- **Tasti Avvia/Ferma**: ora **verde e rosso, più grandi**.

### Controlli
- `check_status.py` **[22]**: batteria bassa rimossa, stima col SoC programmato, tagliando unico, wallbox.

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
