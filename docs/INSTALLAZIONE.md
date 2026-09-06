# Guida all'installazione — Renault EV Center

Questa guida ti accompagna passo-passo dall'installazione alla prima dashboard completa.
Tempo richiesto: **~10 minuti**.

---

## 0. Prerequisiti

- Home Assistant **2025.11 o superiore**
- Integrazione **Renault** già configurata e funzionante
  (*Impostazioni → Dispositivi e servizi → Renault*): devi vedere la tua auto con i sensori attivi
- *(Opzionale ma consigliato)* Wallbox integrata in HA

> 💡 **Come verificare:** cerca `sensor.mileage` in Strumenti per sviluppatori → Stati. Se esiste ed è aggiornata, sei a posto.

## 1. Installare l'integrazione

### Con HACS (consigliato)

1. Apri **HACS** nella barra laterale
2. In basso a destra: **⋮ → Repository personalizzati**
3. Inserisci:
   ```
   https://github.com/Redrex85/Renault-EV-Center-Home-Assistant
   ```
4. Categoria: **Integrazione** → **Aggiungi**
5. Cerca "Renault EV Center" → **Scarica**
6. **Riavvia Home Assistant** (Strumenti per sviluppatori → YAML → Riavvia, o Impostazioni → Sistema)

### Manuale

1. Scarica lo zip della release da GitHub
2. Estrai `custom_components/renault_ev_center/`
3. Copialo in `<config>/custom_components/renault_ev_center/`
4. Riavvia HA

## 2. Configurazione guidata

1. **Impostazioni → Dispositivi e servizi → + Aggiungi integrazione**
2. Cerca **"Renault EV Center"**

### Schermata 1 — L'auto

| Campo | Cosa scegliere | Tipicamente |
|---|---|---|
| Nome dell'auto | Nome breve, minuscolo | `Renault` |
| Modello | Imposta in automatico la **foto dell'auto** | Megane E-Tech |
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

Se l'hai disattivata o vuoi farla a mano: i file sono in [`dashboards/`](../dashboards/) —
Impostazioni → Dashboard → Aggiungi → matita → ⋮ → *Modifica configurazione UI in YAML* → incolla.

> 🔄 Prefisso sbagliato? Trova-sostituisci `sensor.renault_` nei file con il tuo prefisso.
>
> 🗺️ La card **mappa** richiede il tracker GPS: se non lo hai, elimina quel blocco.

## 4. Verifica finale

In Strumenti per sviluppatori → Stati cerca `sensor.renault_km_per_kwh`.
Dopo qualche minuto di guida dovresti vedere valori realistici (5–6 km/kWh in città).

I **viaggi** vengono rilevati automaticamente quando l'odometro aumenta; il viaggio si chiude dopo i minuti di timeout configurati.

## 5. Automazioni consigliate

Copia ciò che ti serve da [`examples/automazioni_esempio.yaml`](../examples/automazioni_esempio.yaml):

- 🔔 Notifica **ricarica completata** con kWh e costo
- ⚠️ Avviso **batteria bassa** fuori casa
- 📊 **Riassunto serale** dei km della giornata

Sostituisci `notify.persistent_notification` con il tuo servizio di notifica (es. `notify.mobile_app_tuo_telefono`).

## 6. Problemi comuni

| Problema | Soluzione |
|---|---|
| L'integrazione non appare in HACS | Controlla di averla aggiunta come categoria **Integrazione** e di aver riavviato |
| Sensori "non disponibili" | Il cloud Renault aggiorna lentamente; attendi o riavvia l'integrazione Renault |
| Km giornalieri sempre 0 | Controlla di aver scelto il giusto odometro nel config flow |
| Costi a zero | Verifica i prezzi nelle opzioni; senza wallbox i costi si accumulano solo su ricariche manuali |
| I viaggi non si chiudono | Riduci il "timeout viaggi" nelle opzioni (es. 10 min) |
| Dashboard mostrano "entità non trovata" | Prefisso sbagliato: trova-sostituisci `sensor.megane_` nei file YAML |

## 7. Backup e dati

Tutti i dati sono in `<config>/.storage/renault_ev_center.<entry_id>`.
Includi `.storage` nei tuoi backup! Per esportare i viaggi usa il pulsante **Esporta Viaggi CSV** oppure il servizio `renault_ev_center.export_trips_csv` (i file finiscono in `config/renault_ev_center_export/`).

Buon divertimento con la tua elettrica! 🚗⚡
