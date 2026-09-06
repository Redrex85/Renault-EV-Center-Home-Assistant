# Relazione integrazione Home Assistant - Renault EV Center

Data analisi: 2026-09-06

## Sintesi

L'integrazione `renault_ev_center` e' gia' in uno stato avanzato: struttura HACS presente, config flow disponibile, piattaforme Home Assistant separate, coordinator centrale, servizi custom, dashboard Lovelace e documentazione. I vecchi blocchi gravi indicati in `REVIEW.md` risultano in gran parte gia' risolti: gli import mancanti, la finestra di carica notturna, il refresh dei controlli dashboard e la firma dell'early-exit sono presenti nel codice attuale.

Non ho rilevato errori sintattici Python nei file dell'integrazione tramite controllo AST in sola lettura. Non ho eseguito `tools/check_status.py` perche' usa `py_compile` e potrebbe creare cartelle `__pycache__`, mentre la richiesta era di analizzare senza toccare nulla.

Verdetto: non vedo un blocco immediato di caricamento, ma prima di considerarla pronta per pubblicazione o uso stabile conviene sistemare alcune aree di robustezza, soprattutto persistenza delle scadenze, gestione multi-entry, traduzioni UI e naming moderno delle entita'.

## Problemi e migliorie consigliate

## 1. Persistenza delle scadenze incompleta

Priorita': alta

In `coordinator.py` i servizi modificano `self.store.data["scadenze"]`, per esempio `service_renew_insurance`, `service_set_scadenza` e `service_set_tagliando`.

Pero' in `store.py`, nel metodo `save()`, il payload salvato include viaggi, ricariche, storico giornaliero, contatori, salute batteria, manutenzione e km mensili, ma non include `scadenze`.

Impatto:

- assicurazione, bollo, revisione e tagliando impostati via servizio possono non essere persistiti correttamente;
- al reload o dopo salvataggi successivi si rischia di tornare ai valori iniziali/configurati;
- la UI puo' mostrare dati apparentemente aggiornati solo finche' restano in memoria.

Suggerimento: aggiungere `scadenze` al payload di `MateStore.save()` e inizializzarlo nei dati di default dello store.

## 2. Servizi applicati a tutte le entry

Priorita': alta se si vuole supportare piu' veicoli

In `__init__.py` i service handler usano `_all_coordinators(hass)` e applicano l'azione a tutte le configurazioni attive.

Esempi:

- `reset_counters`
- `add_manual_charge`
- `delete_trip`
- `add_maintenance`
- `renew_insurance`
- `set_scadenza`
- `set_tagliando`
- `create_dashboard`

Impatto:

- con una sola auto non si nota;
- con due o piu' auto, una chiamata servizio puo' modificare tutte le auto;
- un reset contatori o una cancellazione viaggio rischia di essere distruttiva su entry non intenzionate.

Suggerimento: aggiungere un campo `entry_id` o un target basato su entita'/device, oppure registrare servizi che possano determinare il coordinator a partire da una entity target. Per i servizi distruttivi, meglio obbligare un target esplicito quando ci sono piu' entry.

## 3. `export_trips_csv` e `SupportsResponse.OPTIONAL`

Priorita': media

Il servizio `export_trips_csv` e' registrato con `SupportsResponse.OPTIONAL`, ma l'handler ritorna sempre un dizionario con i percorsi esportati.

Secondo le API Home Assistant, con `OPTIONAL` l'handler dovrebbe controllare `call.return_response` e restituire dati solo quando richiesti, oppure usare `SupportsResponse.ONLY` se il servizio e' pensato principalmente per restituire una risposta.

## 4. Naming entita' non allineato alle best practice moderne

Priorita': media

Le classi base usano `_attr_has_entity_name = False` in sensori, binary sensor, button, number, select, switch e time.

Le linee guida moderne di Home Assistant raccomandano per nuove integrazioni `has_entity_name=True`, con nome dispositivo separato dal nome della singola entita'.

Impatto:

- non e' un errore runtime;
- puo' penalizzare qualita' dell'integrazione, consistenza UI e readiness HACS;
- rende piu' difficile introdurre traduzioni entity-name pulite.

Suggerimento: valutare una migrazione controllata a `has_entity_name=True`, evitando pero' di rompere entity_id gia' usati dagli utenti.

## 5. Traduzioni config flow incomplete o non allineate

Priorita': media

Nel config flow alcuni campi sono nello step `settings`, ma in `strings.json` alcune label risultano assenti o collocate sotto altri step.

Campi da verificare:

- `wb_charge_switch`
- `has_pv`
- `balance_grid_sensor`
- `balance_battery_sensor`
- `balance_invert_grid`
- `balance_include_battery`
- `balance_watts_per_amp`
- `balance_battery_soc_sensor`
- `battery_priority_min`
- `charge_target_number`
- `temp_entity`
- `co2_comparison`
- `co2_thermal_gkm`
- `co2_grid_gkwh`
- `scadenze_enabled`
- `scadenza_bollo`
- `scadenza_revisione`
- `scadenza_assicurazione`

Impatto:

- la UI del config flow/options flow puo' mostrare chiavi tecniche invece di etichette leggibili;
- l'esperienza utente peggiora soprattutto nella configurazione avanzata.

## 6. Attributi sensori potenzialmente molto grandi

Priorita': media/bassa

Alcuni sensori espongono liste e report negli attributi: archivio viaggi, lista ricariche, report generale, storico giornaliero, rotte/zone e sessioni salute batteria.

Impatto:

- gli attributi vengono salvati nello state machine e possono finire nel recorder;
- troppi dati negli attributi possono appesantire database e frontend;
- dashboard piu' lente con storico ampio.

Suggerimento: mantenere negli attributi solo gli ultimi record necessari alla dashboard e lasciare lo storico completo al servizio CSV.

## 7. Dashboard automatica fragile tra versioni HA

Priorita': media

`dashboard.py` usa API interne Lovelace e gestisce piu' varianti di Home Assistant, inclusa una modalita' fallback con YAML e notifica persistente.

Impatto:

- buon approccio difensivo, ma le API Lovelace interne possono cambiare;
- la creazione/rimozione automatica dashboard va testata su piu' versioni HA;
- su alcuni ambienti potrebbe servire il piano B manuale.

## 8. Gestione errori del coordinator troppo permissiva

Priorita': media/bassa

In `_async_update_data()` il coordinator intercetta qualunque eccezione, logga un warning e ritorna i dati precedenti se disponibili.

Impatto:

- ottimo per non rompere la UI su errori temporanei;
- rischia pero' di mascherare errori persistenti di configurazione o bug runtime;
- l'utente puo' vedere dati vecchi pensando che siano aggiornati.

Suggerimento: contare errori consecutivi e dopo una soglia alzare `UpdateFailed` o rendere il problema piu' visibile.

## 9. Notifiche: fallback senza `title`

Priorita': bassa

`_send_notify()` invia sempre payload con `title` e `message`.

Impatto:

- molte piattaforme notify lo supportano;
- alcune potrebbero accettare solo `message`;
- in quel caso la notifica fallisce e resta solo il warning.

Suggerimento: in caso di errore, ritentare con payload solo `message`, concatenando titolo e messaggio.

## 10. Rimozione entry: cancellazione comune di `/config/www/renault-ev-center`

Priorita': media se si supporta multi-entry

In `async_remove_entry()` viene rimossa tutta la directory `/config/www/renault-ev-center`.

Impatto:

- con una sola entry e' comprensibile;
- con piu' auto, rimuovere una entry puo' cancellare risorse condivise ancora usate dalle altre;
- eventuali file custom dell'utente messi in quella cartella potrebbero sparire.

Suggerimento: cancellare la cartella solo quando non rimangono altre entry dell'integrazione, oppure separare file per entry e file condivisi.

## Test consigliati prima della pubblicazione

1. Installazione pulita da HACS.
2. Config flow nuova entry.
3. Options flow dopo installazione.
4. Avvio HA e verifica log senza `NameError` o warning ripetuti.
5. Verifica entita' create e nomi entity_id generati.
6. Verifica dashboard automatica e fallback YAML.
7. Modifica dei `number` da dashboard e verifica che influenzino davvero i sensori.
8. Carica programmata in modalita' orario con finestra notturna `23:30 -> 07:00`.
9. Carica programmata in modalita' percentuale.
10. Promemoria batteria bassa.
11. Bilanciamento solare con sensore rete, inversione segno, number corrente wallbox e limiti ampere.
12. Servizi custom principali: ricariche manuali, viaggi, manutenzione, assicurazione, scadenze, export CSV.
13. Riavvio HA e verifica persistenza di viaggi, ricariche, manutenzioni, scadenze, contatori e impostazioni.
14. Rimozione integrazione e verifica cleanup.

## Ordine consigliato degli interventi

1. Salvare `scadenze` in `MateStore.save()` e nei dati default.
2. Rendere i servizi sicuri per multi-entry.
3. Allineare `strings.json` e `translations/*.json` al config flow reale.
4. Migliorare `export_trips_csv` rispetto a `SupportsResponse`.
5. Aggiungere fallback notify senza `title`.
6. Ridurre o controllare meglio gli attributi molto grandi.
7. Pianificare migrazione entity naming a `has_entity_name=True`.
8. Testare dashboard automatica su versioni HA diverse.

## Conclusione

Renault EV Center e' una integrazione ricca e ben strutturata, con un set di funzioni superiore a una semplice raccolta sensori: viaggi, ricariche, costi, manutenzione, risparmi, fotovoltaico, automazioni e dashboard dedicata.

La base e' buona. I problemi rimasti non sembrano blocchi sintattici immediati, ma sono importanti per affidabilita', esperienza utente e pubblicazione. La correzione piu' urgente e' la persistenza delle `scadenze`, seguita dalla gestione multi-entry dei servizi.

Una volta sistemati questi punti e validata l'integrazione in Home Assistant reale, il progetto puo' arrivare a un livello molto piu' solido per uso quotidiano e distribuzione HACS.
