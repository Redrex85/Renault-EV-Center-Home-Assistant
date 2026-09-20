# Guide d'installation — Renault EV Center

De l'installation au tableau de bord opérationnel en **~10 minutes**.

## Prérequis

- Home Assistant **2025.11+**
- L'intégration officielle **Renault** configurée avec votre véhicule
- *(Optionnel)* Une wallbox intégrée dans HA (Wallbox, go-e, Easee, OCPP, Shelly EM…)

## 1. Installation

**HACS :** HACS → ⋮ → Dépôts personnalisés → ajouter `https://github.com/Redrex85/Renault-EV-Center-Home-Assistant` (catégorie : Intégration) → **puis cherchez « Renault EV Center » dans HACS → ouvrez-le → Télécharger** → **redémarrez Home Assistant** → **Paramètres → Appareils et services → Ajouter une intégration → « Renault EV Center »** → lancez l'assistant.

> En bref : **dépôt → recherche dans HACS → télécharger → redémarrer → ajouter l'intégration → configurer**.
> Le redémarrage est obligatoire : HA ne charge les nouvelles intégrations qu'au démarrage, donc avant
> cela « Renault EV Center » n'apparaît pas dans la recherche.

**Manuel :** copiez `custom_components/renault_ev_center/` dans `<config>/custom_components/`, redémarrez HA.

## 2. Configuration

Paramètres → Appareils et services → Ajouter une intégration → **Renault EV Center** :

### Étape 0 — Profil d'installation (le tout premier écran)
La **toute première** question est le **profil** : il détermine **quels écrans** vous verrez pendant
la configuration et **quelles pages** apparaîtront dans le tableau de bord.

| Profil | Inclut | Vous ne verrez pas |
|---|---|---|
| **Base** — voiture seule | voiture, trajets, coûts, recharges, économies, entretien | **pas de wallbox**, **pas de solaire**, et la **page Wallbox est masquée** |
| **Pro** — voiture + wallbox | Base **+ wallbox** (démarrage/arrêt, puissance, session, GSE) | pas de solaire |
| **Enterprise** — tout | Pro **+ solaire** et équilibrage solaire | — |

> Choisissez **Base** si vous n'avez pas de wallbox dans Home Assistant (recharges publiques
> uniquement) : configuration plus courte, panneau plus propre. Modifiable ensuite via
> *Paramètres → Intégrations → Renault EV Center → ⋮ → Configurer*.

### Étape 1 — Voiture
Choisissez un nom court en minuscules (`Megane`) — il devient le préfixe des entités — puis sélectionnez :
odomètre (`sensor.mileage`), niveau batterie (`sensor.battery_level`), autonomie (`sensor.battery_autonomy`),
en charge (`binary_sensor.charging` ou `sensor.charge_state`), statut prise et tracker GPS optionnels.
Choisissez aussi le **modèle** (premier champ : il définit la photo).

### Étape 2 — Wallbox *(ignorée avec le profil Base)*
Activez l'interrupteur et mappez : puissance instantanée (W ou kW, conversion auto), état du chargeur, compteur énergie session et/ou total. Aussi ici : les entités **démarrage / arrêt** et la section **Expérimentation GSE**.

Pas de wallbox ? Choisissez le profil **Base** — les recharges publiques s'enregistrent à la main avec le service `add_manual_charge`.

### Étape 3 — Paramètres
Capacité batterie, SoC cible, tarifs domicile/public/solaire, zone solaire, intervalle, timeout trajets, comparaison carburant, CO₂, échéances, services de notification. Tout est modifiable ensuite via Configurer.
Si la voiture a **déjà roulé** avant l'installation, remplissez aussi **« kWh rechargés avant »**
et/ou **« € dépensés avant »** (voir §4.2 — sinon les économies paraissent gonflées).

## 3. Tableaux de bord

Si vous avez coché **Créer le tableau de bord automatiquement**, il apparaît seul dans la barre latérale. Sinon, importez les YAML de [`dashboards/`](../dashboards/) manuellement.

Préfixe différent de `Renault` ? Faites Rechercher/Remplacer `sensor.renault_`.

## 4.1 Confidentialité et adresses (géocodage)

Sur la page **Trajets**, l'intégration peut afficher la **rue et le pays** de départ/arrivée,
à partir des coordonnées GPS via **OpenStreetMap (Nominatim)**.

- **Activé par défaut.** Pour le **désactiver** (aucun appel externe, aucune adresse) :
  *Paramètres → Appareils et services → Renault EV Center → **Configurer** → Paramètres →
  « Rue et pays dans les trajets »* (décochez).
- Les coordonnées sont **arrondies** et mises en **cache locale** : le géocodage ne s'exécute
  qu'une fois par lieu et à la fermeture d'un trajet.
- **« Vitesse moyenne estimée »** (défaut 30 km/h) : sert uniquement à estimer l'heure de départ
  quand la voiture est restée longtemps garée (le cloud Renault met à jour à l'arrêt moteur).
  Augmentez-la si vos trajets sont plus rapides.

## 4.2 Économies sur une voiture **déjà roulée** (important)

L'économie compare **ce que vous auriez dépensé en essence/diesel** avec **ce que vous avez
dépensé en recharge**. Le piège : les kilomètres viennent de l'**odomètre** (donc ils comptent
**tous**, y compris les 40.000 faits avant), mais les recharges ne sont enregistrées que **depuis
l'installation**. Sans correction l'économie serait **gonflée**.

Il y a **deux comparaisons**, et le panneau (Risparmi → *🎯 Confronto affidabilità*) affiche les deux :

### A) Depuis l'installation — la plus fiable ✅
Les deux côtés viennent de **données réelles** :
- **km parcourus depuis l'installation** (odomètre d'aujourd'hui − celui du premier démarrage, enregistré automatiquement) ;
- **recharges enregistrées** depuis ce moment.

Rien à saisir, aucune estimation.

### B) Depuis toujours — nécessite les valeurs déclarées
Utilise **tout l'odomètre** contre **recharges enregistrées + celles que vous déclarez**.
Dans *Configurer → Prix*, remplissez **au moins un** des deux champs :

| Champ | Quand l'utiliser |
|---|---|
| **€ dépensés avant** | si vous connaissez déjà le montant (**prioritaire** sur les kWh) |
| **kWh rechargés avant** | si vous connaissez les kWh (ex. le **total de la wallbox**) ; convertis en € avec le *Prix énergie maison* |

Exemple : la voiture a 40.000 km et la wallbox indique **8 326,4 kWh** → mettez `8326.4` dans
*kWh rechargés avant*.

**Ce qui change quand vous les remplissez** — ce n'est pas seulement la case « Confronto affidabilità » :
les valeurs déclarées alimentent **tous** les chiffres de la page Économies :
- la ligne **« 🕘 Ricariche prima (dichiarate) »** du tableau thermique vs électrique ;
- le **total électrique**, la **Différence** par ligne et le **★ NETTO** ;
- le **graphique à barres** « Confronto costi » (barre verte) ;
- le capteur **`Risparmio Totale vs Diesel`** → donc aussi la carte **Risparmio netto** dans *Panoramica*.

Autrement dit : **remplissez ces deux champs et la page Économies devient complète et fiable** sur
toute la vie de la voiture — pas seulement dans la case de comparaison. Laissez-les vides et le
« depuis toujours » reste **gonflé** (avertissement ⚠️) : regardez alors la comparaison **A**.

> Les valeurs déclarées concernent le **total « depuis toujours »**. **Mois** et **année** restent
> calculés sur les données réelles de la période : par définition plus petits — ce n'est pas une erreur.

**Vous n'avez rien à choisir au départ** : le panneau calcule et affiche **toujours les deux**.
- **A** fonctionne seule dès le premier démarrage, sans configuration.
- **B** s'active quand vous remplissez les champs ci-dessus. Tant qu'ils restent à `0` et que la
  voiture avait déjà des kilomètres, le panneau affiche un **avertissement** : la comparaison
  « depuis toujours » n'est pas exploitable.

> Si vous remplissez les valeurs déclarées puis regardez la comparaison **A**, les deux nombres
> diffèrent par définition : A couvre seulement la période après l'installation, B toute la vie de
> la voiture. Ce n'est pas une erreur : ce sont deux questions différentes.

## 4. Services, FAQ et dépannage
Les automatisations recommandées peuvent être créées depuis la vue **Automazioni → « Crea automazioni consigliate »** (ou le service `renault_ev_center.create_automations`).
Voir `docs/INSTALLATION.md` (EN) pour la référence complète.
