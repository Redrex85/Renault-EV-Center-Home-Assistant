# Guide d'installation — Renault EV Center

De l'installation au tableau de bord opérationnel en **~10 minutes**.

## Prérequis

- Home Assistant **2025.11+**
- L'intégration officielle **Renault** configurée avec votre véhicule
- *(Optionnel)* Une wallbox intégrée dans HA (Wallbox, go-e, Easee, OCPP, Shelly EM…)

## 1. Installation

**HACS :** HACS → ⋮ → Dépôts personnalisés → ajouter `https://github.com/Redrex85/Renault-EV-Center-Home-Assistant` (catégorie : Intégration) → télécharger → redémarrer HA.

**Manuel :** copiez `custom_components/renault_ev_center/` dans `<config>/custom_components/`, redémarrez HA.

## 2. Configuration

Paramètres → Appareils et services → Ajouter une intégration → **Renault EV Center** :

### Étape 1 — Voiture
Choisissez un nom court en minuscules (`Megane`) — il devient le préfixe des entités — puis sélectionnez :
odomètre (`sensor.mileage`), niveau batterie (`sensor.battery_level`), autonomie (`sensor.battery_autonomy`),
en charge (`binary_sensor.charging` ou `sensor.charge_state`), statut prise et tracker GPS optionnels.
Le modèle choisit automatiquement la photo de la voiture et la langue suit celle de votre profil HA.

### Étape 2 — Wallbox
Activez l'interrupteur et mappez : puissance instantanée (W ou kW, conversion auto), état du chargeur, compteur énergie session et/ou total. La vue Gestion Recharge n'apparaît qu'avec une wallbox.

Pas de wallbox ? Laissez tout désactivé — les recharges publiques seront estimées via le delta SoC et le profil Minimal masquera les sections wallbox.

### Étape 3 — Paramètres
Capacité batterie, SoC cible, tarifs domicile/public/solaire, zone solaire, intervalle, timeout trajets, comparaison carburant, CO₂, échéances, services de notification. Tout est modifiable ensuite via Configurer.

## 3. Tableaux de bord

Si vous avez coché **Créer le tableau de bord automatiquement**, il apparaît seul dans la barre latérale. Sinon, importez les YAML de [`dashboards/`](../dashboards/) manuellement.

Préfixe différent de `Renault` ? Faites Rechercher/Remplacer `sensor.renault_`.

## 4. Services, FAQ et dépannage
Voir `docs/INSTALLATION.md` (EN) pour la référence complète.
