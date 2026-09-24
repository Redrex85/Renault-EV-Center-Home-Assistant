# Guida all'installazione — Renault EV Center

Questa guida ti accompagna passo-passo dall'installazione alla prima dashboard completa.
Tempo richiesto: **~10 minuti**.

---

## 0. Prerequisiti

- Home Assistant **2025.11 o superiore**
- Integrazione **Renault** già configurata e funzionante
  (*Impostazioni → Dispositivi e servizi → Renault*): devi vedere la tua auto con i sensori attivi
- *(Opzionale ma consigliato)* Wallbox integrata in HA

> ⚠️ **Fortemente consigliato: almeno la zona Casa.** In HA vai su
> **Impostazioni → Zone** e assicurati che esista una zona `Casa` (latitudine e
> longitudine corrette) con dentro il **tracker GPS dell'auto**. Senza la zona `home`
> l'integrazione **non distingue una ricarica a casa da una colonnina pubblica**:
> tutto finisce come *Pubblica* e i prezzi casa/fotovoltaico non si applicano.

> ⚠️ **Alcuni valori si popolano solo guidando**: viaggi, kWh/100km, efficienza per
> zona, orario di partenza, range reale e storico mensile restano vuoti finché l'auto
> non percorre **qualche decina di km**. Subito dopo l'installazione è normale vedere `—`.

> 💡 **Come verificare:** cerca `sensor.mileage` in Strumenti per sviluppatori → Stati. Se esiste ed è aggiornata, sei a posto.

## 1. Installare l'integrazione

### Con HACS (consigliato)

1. Apri **HACS** nella barra laterale
2. In basso a destra: **⋮ → Repository personalizzati**
3. Inserisci:
   ```
   https://github.com/Redrex85/Renault-EV-Center-Home-Assistant
   ```
4. Categoria: **Integrazione** e poi premi **Aggiungi**
5. Sempre in HACS, **cerca "Renault EV Center"** (compare tra le integrazioni) → aprila → **Scarica**
6. **Riavvia Home Assistant** (Strumenti per sviluppatori → YAML → Riavvia, o Impostazioni → Sistema)
7. Dopo il riavvio: **Impostazioni → Dispositivi e servizi → + Aggiungi integrazione** →
   cerca **"Renault EV Center"** e **avvia la configurazione guidata** (vedi §2)

> ⚠️ **A volte la dashboard non si apre alla prima apertura**: se dopo aver aggiunto l'integrazione
> il pannello risulta vuoto o non caricato, **riavvia nuovamente Home Assistant** (una seconda volta)
> e ricarica la pagina con **Ctrl+Shift+R**. La dashboard e le risorse JS vengono copiate durante il
> setup: HA ha bisogno di un ciclo completo per registrarle.

> In breve: **repo → cerca in HACS → scarica → riavvia → aggiungi l'integrazione → configura**.
> Il riavvio serve perché HA carica le integrazioni nuove solo all'avvio; senza di esso
> "Renault EV Center" non compare nella ricerca delle integrazioni.

### Manuale

1. Scarica lo zip della release da GitHub
2. Estrai `custom_components/renault_ev_center/`
3. Copialo in `<config>/custom_components/renault_ev_center/`
4. Riavvia HA

## 2. Configurazione guidata

1. **Impostazioni → Dispositivi e servizi → + Aggiungi integrazione**
2. Cerca **"Renault EV Center"**

### Schermata 0 — Profilo di installazione (la prima!)

La **primissima cosa** che ti viene chiesta è il **profilo**: decide **quali schermate** vedrai
durante la configurazione e **quali pagine** compariranno nella dashboard.

| Profilo | Cosa include | Cosa NON vedrai |
|---|---|---|
| **Base** — solo auto | auto, viaggi, costi, ricariche, risparmi, manutenzione | **niente wallbox**, **niente fotovoltaico**, e la **pagina Wallbox non compare** nel pannello |
| **Pro** — auto + wallbox | tutto il Base **+ wallbox** (avvio/stop, potenza, sessione, GSE) | niente fotovoltaico |
| **Enterprise** — tutto | Pro **+ fotovoltaico** e bilanciamento solare | — |

> Scegli **Base** se non hai una wallbox in Home Assistant (carichi solo alle colonnine): la
> configurazione sarà più corta e il pannello più pulito. Puoi cambiare profilo in seguito da
> *Impostazioni → Integrazioni → Renault EV Center → ⋮ → Configura*.

### Schermata 1 — L'auto

| Campo | Cosa scegliere | Tipicamente |
|---|---|---|
| Modello | Imposta in automatico la **foto dell'auto** | Megane E-Tech |
| Nome dell'auto | Nome breve, minuscolo | `Renault` |
| Crea dashboard | Plancia laterale con tutte le viste, creata da sola | ✅ |
| Odometro | Sensore chilometraggio | `sensor.mileage` |
| Livello batteria (%) | Sensore % batteria | `sensor.battery_level` |
| Autonomia residua | Sensore autonomia km | `sensor.battery_autonomy` |
| In carica | Binary sensor o sensore stato carica | `binary_sensor.charging` |
| Stato spina | Opzionale | `sensor.plug_state` |
| Tracker GPS | Opzionale (mappa e zone viaggi) | `device_tracker.location` |

> ⚠️ Il **nome dell'auto diventa il prefisso** di tutte le entità create (`sensor.renault_km_giornalieri`, …).
>
> ✅ Al termine **la dashboard viene creata automaticamente** nella barra laterale
> ("«Nome» EV Center") con tutte le viste già pronte. La foto del modello viene copiata in
> `/config/www/renault-ev-center/auto.png` — sostituiscila con una foto reale se vuoi.

### Schermata 2 — La wallbox

Attiva **"Ho una wallbox in Home Assistant"** e seleziona:

| Campo | Cosa scegliere | Esempio Wallbox/OCPP/go-e |
|---|---|---|
| Potenza istantanea | W o kW — conversione automatica | `sensor.wallbox_instant_power` |
| Stato wallbox | Lo stato tipo "charging" | `sensor.wallbox_charger_state` |
| Contatore energia sessione | kWh sessione corrente | se disponibile |
| Contatore energia totale | kWh totali erogati | alternativa al precedente |
| Avvio/stop carica | Switch o button della wallbox (per la carica programmata) | se disponibile |
| Target di carica | Number Renault (fallback per lo stop) | opzionale |

Se non hai una wallbox lascia tutto disattivato: le ricariche pubbliche potranno essere registrate manualmente.

### Schermata 3 — Impostazioni

| Campo | Significato | Default Megane |
|---|---|---|
| Capacità batteria | kWh utili della tua auto | 60 kWh (EV60) |
| Obiettivo Ricarica | % target per le stime e l'automazione fine carica | 80% |
| Prezzo energia casa | €/kWh contratto domestico | 0.25 |
| Prezzo colonnine | €/kWh media pubblica | 0.45 |
| Costo fotovoltaico | €/kWh solare (0 = gratis) | 0.00 |
| Zona fotovoltaico | Nome zona HA dove carichi col solare | `beb` |
| **kWh caricati prima** | kWh caricati **prima** di usare l'integrazione (vedi §5.2) | 0 |
| **€ spesi prima** | € già spesi in ricariche prima dell'integrazione (priorità sui kWh) | 0 |
| Intervallo aggiornamento | Frequenza lettura sensori | 30 s |
| Timeout viaggi | Minuti di odometro fermo = fine viaggio | 20 min |
| Confronto termica | Risparmi vs diesel/benzina (tagliando medio 450 €) | opzionale |
| Servizio notifiche | Es. `notify.michele` — per scadenze e ricariche | opzionale |
| Giorni preavviso | Quanti giorni prima avvisare delle scadenze | 30 |
| Promemoria batteria bassa | % minima + fascia oraria | 25% · 18–22 |
| Carica programmata | Modalità orario/percentuale + orari e % | opzionale |

**Modifiche successive:** Impostazioni → Integrazioni → Renault EV Center → ⋮ → **Configura**.

## 3. Le dashboard

Con l'opzione attiva **non devi fare nulla**: la plancia appare da sola nella barra laterale
con 11 viste (Panoramica, Viaggi, Statistiche, Ricariche, Salute batteria, Manutenzione,
Risparmi, Extra, Automazioni, Impostazioni, Mobile).

Se l'hai disattivata o è stata rimossa: esegui il servizio `renault_ev_center.create_dashboard`
(Strumenti per sviluppatori → Azioni) — ricostruisce il pannello **con il prefisso entità giusto**,
senza YAML manuale.

> ⚠️ I file in [`dashboards/`](../dashboards/) sono **legacy**: hanno `sensor.renault_` scritto
> in fisso, quindi si rompono con qualsiasi auto non chiamata letteralmente `Renault`.
> Non importarli — il pannello auto-creato copre già tutto.
>
> 🗺️ La card **mappa** richiede il tracker GPS: se non lo hai, elimina quel blocco.

## 4. Verifica finale

In Strumenti per sviluppatori → Stati cerca `sensor.renault_km_per_kwh`.
Dopo qualche minuto di guida dovresti vedere valori realistici (5–6 km/kWh in città).

I **viaggi** vengono rilevati automaticamente quando l'odometro aumenta; il viaggio si chiude dopo i minuti di timeout configurati.

## 5. Automazioni consigliate

Puoi crearle in automatico dalla vista **Automazioni → "Crea automazioni consigliate"**
(oppure col servizio `renault_ev_center.create_automations`).

In alternativa copia ciò che ti serve da [`examples/automazioni_esempio.yaml`](../examples/automazioni_esempio.yaml):

- 🔔 Notifica **ricarica completata** con kWh e costo
- ⚠️ Avviso **batteria bassa** fuori casa
- 📊 **Riassunto serale** dei km della giornata

Sostituisci `notify.persistent_notification` con il tuo servizio di notifica (es. `notify.mobile_app_tuo_telefono`).

## 5.1 Privacy e indirizzi (geocoding)

Nei **Viaggi** l'integrazione può mostrare **via e paese** di partenza/arrivo, ricavati dalle
coordinate GPS con **OpenStreetMap (Nominatim)**.

- **Attivo di default.** Per **disattivarlo** (nessuna chiamata esterna, nessun indirizzo):
  *Impostazioni → Integrazioni → Renault EV Center → **Configura** → Impostazioni →
  "Via e paese nei viaggi"* (togli la spunta).
- Le coordinate sono **arrotondate** e messe in **cache locale**: il geocoding gira una volta
  per posizione e solo alla chiusura di un viaggio.
- **"Velocità media stimata nei viaggi"** (default 30 km/h): serve solo a **stimare l'orario di
  partenza** quando l'auto è rimasta ferma a lungo (il cloud Renault aggiorna odometro/GPS a
  motore spento). Alzatela se i tuoi viaggi sono più veloci.

## 5.2 Risparmi con un'auto **già percorsa** (importante)

Il risparmio confronta **quello che avresti speso a benzina/diesel** con **quello che hai speso
in ricariche**. Il problema: i km li prendo dall'**odometro** (quindi contano **tutti**, anche i
40.000 fatti prima), ma le ricariche le registro **solo da quando usi l'integrazione**. Senza
correzione il risparmio risulterebbe **gonfiato**.

Ci sono **due confronti**, e il pannello (Risparmi → *🎯 Affidabilità del confronto*) li mostra
entrambi:

### A) Da installazione — il più attendibile ✅
Entrambi i lati nascono da **dati reali**:
- **km percorsi da quando hai installato** (odometro di oggi − odometro del primo avvio, salvato in automatico);
- **ricariche registrate** da lì in poi.

Nessun valore da inserire, nessuna stima. È il numero da guardare se vuoi la verità "matematica".

### B) Da sempre — richiede i valori dichiarati
Usa **tutto l'odometro** contro **ricariche registrate + quelle che dichiari tu**.
Vai in *Configura → Prezzi* e compila **almeno uno** dei due campi:

| Campo | Quando usarlo |
|---|---|
| **€ spesi prima** | se sai già quanto hai speso in ricariche (ha **priorità** sui kWh) |
| **kWh caricati prima** | se conosci i kWh (es. il **totale della wallbox**); vengono convertiti in € col *Prezzo energia casa* |

Esempio: hai l'auto da 40.000 km e la wallbox segna **8.326,4 kWh** → metti `8326,4` in
*kWh caricati prima*.

**Cosa cambia quando li inserisci** — non è un dettaglio del solo box "Affidabilità del confronto":
i valori dichiarati entrano in **tutti** i numeri dei Risparmi:
- la riga **"🕘 Ricariche prima (dichiarate)"** nella tabella termica vs elettrica;
- il **totale elettrico**, la **Differenza** per riga e il **★ NETTO**;
- il **grafico a barre** "Confronto costi" (barra verde);
- il sensore **`Risparmio Totale vs Diesel`** → quindi anche la card **Risparmio netto** in *Panoramica*.

In pratica: **se compili quei due campi, la pagina Risparmi diventa completa e attendibile** su tutto
l'arco di vita dell'auto — non solo nel riquadro di confronto. Se li lasci vuoti, il "da sempre"
resta **gonfiato** (avviso ⚠️) e devi guardare il confronto **A**.

> I valori dichiarati valgono per il **totale "da sempre"**. **Mese** e **anno** restano calcolati
> sui dati reali di quel periodo: sono per definizione più piccoli, non è un errore.

### Quale scegliere?
| Obiettivo | Confronto da usare |
|---|---|
| Risparmio **verificabile** (nessuna stima) | **A) Da installazione** |
| Risparmio **da quando hai l'auto** | **B) Da sempre**, con i valori dichiarati |

**Non devi scegliere nulla all'inizio**: il pannello calcola e mostra **entrambi** sempre.
- **A** funziona da sola dal primo avvio, senza configurazione.
- **B** si attiva quando compili i campi qui sopra. Finché restano a `0` e l'auto aveva già
  chilometri, il pannello mostra un **avviso** (`⚠️ Mancano i kWh/€ caricati prima: questo valore
  è gonfiato`): significa che il confronto "da sempre" non è utilizzabile.

> Se compili i valori dichiarati e poi guardi il confronto **A**, i due numeri sono diversi per
> definizione: A copre solo il periodo dall'installazione, B copre tutta la vita dell'auto.
> Non è un errore: sono due domande diverse.

## 5.3 Bilanciamento casa (non superare il contatore)

Se la wallbox non gestisce da sé il **contatore di casa**, lo fa l'integrazione — senza automazioni YAML.
Nella pagina **Wallbox**, accanto a *Bilanciamento solare*, trovi la card **🏠 Bilanciamento casa** con lo
switch, il **consumo casa** live, la **soglia contatore** e gli **ampere wallbox** attuali.

Configurazione in *Configura → Bilanciamento casa*:

| Campo | Cosa mettere |
|---|---|
| **Sensore consumo casa** | il sensore della potenza di casa (W o kW), es. `sensor.em_power` |
| **Contatore di casa** | **3 · 4.5 · 6 · 10** (= superiore) kW |
| **Ampere a carico alto** | a quanto scendere quando il consumo sale (es. `18`) |
| **Ampere a carico basso** | a quanto tornare quando il consumo cala (es. `25`) |

Logica (derivata dalle soglie del contatore):
- consumo casa **> potenza contatore** per **10 min** → wallbox agli **ampere ridotti**;
- consumo casa **< 80% del contatore** per **15 min** → wallbox agli **ampere ripristinati**;
- in mezzo (80–100%) resta com'è: evita di oscillare.

> Funziona solo **mentre la wallbox carica**. Ogni cambio manda una **notifica** (se hai configurato il
> servizio di notifica). Gli **ampere** sono gli stessi della card *Corrente di carica*: puoi impostarli a mano
> in qualsiasi momento.

## 5.4 Caricare l'auto dalla batteria di casa (di notte)

Di notte non c'è sole: per **non prelevare dalla rete**, l'auto deve prendere dalla **batteria di casa**.
Si fa col **Bilanciamento solare** (che funziona anche di notte, quando il "surplus" è la scarica della batteria):

1. *Configura → Fotovoltaico*: attiva il **Bilanciamento** e **Includi la scarica batteria nel surplus**.
2. Mappa il **Sensore rete** (potenza scambiata/prelevata) e il **Sensore potenza batteria**.
3. Accendi lo switch **☀️ Bilanciamento fotovoltaico** nella pagina *Wallbox*.

Così l'integrazione somma la **scarica della batteria** al surplus e regola gli ampere della wallbox per
tenere il prelievo da rete ~0: di notte l'auto **segue la batteria**, non la rete.

> Se la batteria non basta, la wallbox scende al minimo (6 A) e il resto arriva dalla rete. Per **non
> prelevare mai** dalla rete serve un'automazione che mette in pausa la wallbox quando il prelievo supera
> la soglia del contatore.

> **Wallbox condivisa con altre auto**: la *Sessione corrente* mostra i valori solo se **questa** auto è
> collegata/in carica (sensore spina o stato carica), così le ricariche di altre auto non inquinano i dati.

## 6. Problemi comuni

| Problema | Soluzione |
|---|---|
| L'integrazione non appare in HACS | Controlla di averla aggiunta come categoria **Integrazione** e di aver riavviato |
| Dopo aver aggiunto l'integrazione i sensori non compaiono | **Riavvia Home Assistant**: a volte serve un riavvio perché l'integrazione carichi tutte le piattaforme (sensori, switch, select, time) |
| Sensori "non disponibili" | Il cloud Renault aggiorna lentamente; attendi o riavvia l'integrazione Renault |
| Km giornalieri sempre 0 | Controlla di aver scelto il giusto odometro nel config flow |
| Costi a zero | Verifica i prezzi nelle opzioni; senza wallbox i costi si accumulano solo su ricariche manuali |
| I viaggi non si chiudono | Riduci il "timeout viaggi" nelle opzioni (es. 10 min) |
| Dashboard mostrano "entità non trovata" | Prefisso sbagliato: esegui `renault_ev_center.create_dashboard` (ricostruisce il pannello col prefisso giusto). I file YAML in `dashboards/` sono legacy e vanno evitati |

## 7. Backup e dati

Tutti i dati sono in `<config>/.storage/renault_ev_center.<entry_id>`.
Includi `.storage` nei tuoi backup! Per esportare i viaggi usa il pulsante **Esporta Viaggi CSV** oppure il servizio `renault_ev_center.export_trips_csv` (i file finiscono in `config/renault_ev_center_export/`).

Buon divertimento con la tua elettrica! 🚗⚡
