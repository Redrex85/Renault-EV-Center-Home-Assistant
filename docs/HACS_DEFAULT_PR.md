# PR per entrare nella lista default di HACS

> **Da fare più avanti** (quando i test sono finiti). Questo file è solo preparazione:
> non serve a nessun controllo automatico e non va modificato di fretta.
>
> Obiettivo: aggiungere `Redrex85/Renault-EV-Center-Home-Assistant` a
> [hacs/default](https://github.com/hacs/default) così che l'integrazione
> - compaia nella ricerca di HACS **per tutti**, senza doverla aggiungere come custom repository;
> - venga inclusa in **HACS Data**, con metadati aggiornati **ogni 6 ore** (contro le 48 ore
>   attuali dei custom repository).

---

## 1. Perché farlo

| | Custom repository (ora) | Lista default (dopo la PR) |
|---|---|---|
| Aggiornamento metadati | avvio HA + ogni **48 h** | avvio HA + ogni **6 h** |
| Visibilità | solo chi aggiunge l'URL a mano | tutti gli utenti HACS |
| Entità `update` in HA | sì | sì, popolata da HACS Data |

---

## 2. Pre-flight — da verificare il giorno della PR

Tutti i punti devono essere **verdi** prima di aprire la PR. I requisiti sono quelli ufficiali di
<https://www.hacs.xyz/docs/publish/include/>.

- [ ] **Owner del repo**: la PR può aprirla solo il proprietario o un contributor principale.
      OK, sei tu (`@Redrex85`).
- [ ] **Repo pubblico su GitHub**, con **issues abilitate**, **descrizione** e **topics** impostati.
      Topics già sistemati (era il check che falliva: `home-assistant`, `hacs`, `renault`, …).
- [ ] **`hacs.json` presente e valido** — contiene almeno `name`. ✔
- [ ] **`manifest.json` valido** con `domain`, `documentation`, `issue_tracker`, `codeowners`. ✔
- [ ] **Brand**: `custom_components/renault_ev_center/brand/icon.png` esiste. ✔
- [ ] **HACS Action verde**: workflow `.github/workflows/hacs.yml`. Deve passare **senza errori
      e senza `ignore`** (nel nostro file `ignore` non c'è). Verifica:
      GitHub → *Actions* → **HACS validation** → ultimo run verde.
- [ ] **Hassfest verde**: workflow `.github/workflows/validate.yml` (job `Hassfest (manifest)`).
      Verifica: GitHub → *Actions* → **Validate** → ultimo run verde.
- [ ] **Versione a 3 numeri**: `VERSION` deve essere `x.y.z` (es. `1.0.11`).
      Sul PC: `py tools\check_status.py` → deve finire con `TUTTO OK` (attualmente **97 controlli**).
- [ ] **Almeno una release completa** (una *release*, non solo un tag) creata **dopo** che le
      action sono passate. Verifica:
      ```powershell
      curl -s https://api.github.com/repos/Redrex85/Renault-EV-Center-Home-Assistant/releases/latest
      ```
      Controlla in risposta: `"draft": false` e `"prerelease": false` e `tag_name` = ultima stabile.
- [ ] **Ultima release non pre-release** (le beta servono per i test, ma la PR deve puntare a una
      stabile pubblicata).

> Se un check non passa, **non aprire la PR**: verrebbe chiusa senza avviso.

---

## 3. La modifica (una riga)

1. Fai il **fork** di <https://github.com/hacs/default>.
2. Nel tuo fork crea un **branch nuovo partendo da `master`** (non usare `master` direttamente):
   es. `add-renault-ev-center`.
3. Apri il file **`integration`**.
4. Il file è un **elenco: una repository per riga, in ordine alfabetico**.
   Guarda le prime righe per confermare il formato esatto, poi **inserisci in ordine alfabetico**
   (NON in fondo — c'è un controllo `lint sorted` che fallisce):
   ```
   Redrex85/Renault-EV-Center-Home-Assistant
   ```
5. Commit + push sul branch.
6. Apri la Pull Request verso `hacs/default:master`.

**Attenzioni**
- La PR deve essere **editabile** (il maintainer può richiedere modifiche): non aprirla da un
  account organizzazione.
- Compila **tutto** il template della PR. Un template incompleto = PR chiusa senza avviso.
- Il file `hacs.json` della release deve avere `country` **solo** se l'integrazione è
  limitata a un paese: la nostra no, quindi va lasciato così.

---

## 4. Titolo e corpo PR (pronti da incollare)

**Titolo**
```
Add Redrex85/Renault-EV-Center-Home-Assistant (integration)
```

**Corpo**
```markdown
## Repository
https://github.com/Redrex85/Renault-EV-Center-Home-Assistant

## Type
- [x] Integration

## Description
Renault EV Center is a companion integration for Renault EVs (Megane E-Tech, Scenic E-Tech,
Renault 5, Renault 4, Zoe, Twingo E-Tech, Alpine A290), built on top of the official Home
Assistant Renault integration.

It adds what the core integration does not provide:
- automatic trip detection from the odometer (km, battery used, kWh, efficiency, cost);
- charge sessions with measured wallbox energy, SoC range, duration, type and real cost;
- real costs: €/km, €/100km, per day/week/month/year, separate home/solar/public tariffs;
- battery health: charging efficiency, energy losses, estimated SoH;
- maintenance and road tax tracking, savings vs a thermal car;
- a full Lovelace panel with 11 views plus a sidebar dashboard created automatically;
- scheduled charging (home wallbox or public) with notifications.

## Checklist
- [x] I am the owner of this repository
- [x] The repository is public and hosted on GitHub
- [x] HACS Action passes without errors or ignores
- [x] Hassfest passes (integration)
- [x] `hacs.json` contains at least `name`
- [x] `manifest.json` is valid (domain, documentation, issue_tracker, codeowners)
- [x] Brand assets included (`brand/icon.png`)
- [x] At least one full release published (not just a tag)
- [x] Entry added to `integration` in alphabetical order
```

---

## 5. Cosa succede dopo

1. La PR viene messa in coda: **le nuove inclusioni richiedono mesi** prima di essere riviste
   (non è un rifiuto, è la coda). Backlog:
   <https://github.com/hacs/default/pulls?q=is%3Apr+is%3Aopen+draft%3Afalse+sort%3Acreated-asc>
2. Sul PR girano i controlli automatici, tutti devono passare:
   `brands`, `manifest`, `hacs-validation`, `hacs manifest`, `archived`, `releases`, `owner`,
   `repository` (descrizione + issues + topics), `lint jq`, `lint sorted`.
3. Se ci sono problemi minori la PR viene messa in **draft**: quando hai sistemato, rimettila
   *ready for review*.
4. Dopo il merge, il repo entra nella **scansione schedulata** di HACS Data.
   Da lì: aggiornamenti visibili ad **avvio + ogni 6 h**, per tutti.

---

## 6. Nota di contesto (perché ci siamo arrivati)

Il repo è oggi un **custom repository** per gli utenti: HACS interroga l'API GitHub solo
all'avvio, ogni 48 ore, o quando premi *Aggiorna informazioni*. Ecco perché finora l'aggiornamento
non compariva da solo. Non è un problema dell'integrazione: è il circuito dei custom repository.

Riepilogo dei tempi (fonte: <https://www.hacs.xyz/docs/faq/data_sources/>):

| Evento | Cosa aggiorna |
|---|---|
| Avvio HA | HACS Data (lista default) + GitHub API per i custom |
| ogni 6 h dopo l'avvio | HACS Data → entità `update` delle integrazioni default |
| ogni 48 h dopo l'avvio | GitHub API per i custom repository |
| Apri una repo in HACS | GitHub API per quella repo |
| *Aggiorna informazioni* | GitHub API per quella repo |
| Aggiorna dall'entità `update` | GitHub API per quella repo |
