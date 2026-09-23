# Changelog

Release accorpate: **1.0.4 · 1.0.3 · 1.0.1 · 1.0.0** — le patch `1.0.3.x` / `1.0.4.x`
non esistono più come release separate.
La serie **1.0.5** è ancora attiva come `1.0.5.x`; verrà accorpata in un unico tag `1.0.5`
al passaggio alla **1.0.6** (workflow *Collapse release series*).

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
