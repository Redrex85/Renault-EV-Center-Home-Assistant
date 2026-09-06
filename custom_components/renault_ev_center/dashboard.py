"""Creazione automatica della dashboard laterale e della foto dell'auto."""
from __future__ import annotations

import logging
import os
import re
import shutil
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

WWW_DIR = "renault-ev-center"


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s]", "", str(text).lower())
    return re.sub(r"\s+", "_", s.strip())


def _pkg_dir(*parts: str) -> str:
    return os.path.join(os.path.dirname(__file__), *parts)


def _adjust_prefix(text: str, name: str) -> str:
    slug = slugify(name)
    for dom in ("sensor", "binary_sensor", "number", "select", "button", "switch"):
        text = text.replace(f"{dom}.renault_", f"{dom}.{slug}_")
    return text


def setup_card_js(hass: HomeAssistant) -> None:
    """Copia la card Lovelace dedicata in /config/www (risorsa: /local/...)."""
    src = _pkg_dir("www", "renault-ev-center-card.js")
    dest_dir = hass.config.path("www", WWW_DIR)
    dest = os.path.join(dest_dir, "renault-ev-center-card.js")
    try:
        os.makedirs(dest_dir, exist_ok=True)
        if os.path.isfile(src):
            shutil.copyfile(src, dest)
            _LOGGER.info("Card Lovelace copiata in /local/%s/", WWW_DIR)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Impossibile copiare la card: %s", err)


def setup_car_image(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Copia la foto del modello in /config/www e ritorna il path /local."""
    model = str(entry.data.get("model", "Custom"))
    slug = slugify(model)
    src = _pkg_dir("images", f"{slug}.png")
    dest_dir = hass.config.path("www", WWW_DIR)
    dest = os.path.join(dest_dir, "auto.png")
    try:
        os.makedirs(dest_dir, exist_ok=True)
        if os.path.isfile(src):
            shutil.copyfile(src, dest)
            return f"/local/{WWW_DIR}/auto.png"
        if not os.path.isfile(dest):
            _LOGGER.info(
                "Nessuna immagine per il modello %s: metti la tua foto in %s", model, dest
            )
            return None
        return f"/local/{WWW_DIR}/auto.png"
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Impossibile copiare l'immagine dell'auto: %s", err)
        return None


# parole chiave per nascondere sezioni in base al profilo
MINIMAL_DROP = ("wallbox", "gestione ricarica", "carica programmata", "bilanciamento")


def _section_heading(section: dict[str, Any]) -> str:
    for card in section.get("cards", []) or []:
        h = str(card.get("heading", "")).lower()
        if h:
            return h
    return str(section.get("title", "")).lower()


def _load_bundled_views(name: str, wallbox: bool = True) -> list[dict[str, Any]]:
    """Carica le viste incluse, filtrando per profilo:
    minimal (niente wallbox) → senza sezioni wallbox/gestione."""
    import yaml

    views: list[dict[str, Any]] = []
    d_dir = _pkg_dir("dashboards")
    for fn in sorted(os.listdir(d_dir)):
        if not fn.endswith(".yaml"):
            continue
        if not wallbox and "12_gestione" in fn:
            continue  # vista Gestione ricarica solo con wallbox
        with open(os.path.join(d_dir, fn), encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        for view in raw.get("views", []):
            if not wallbox:
                sezioni = view.get("sections", []) or []
                view["sections"] = [
                    s for s in sezioni
                    if not any(k in _section_heading(s) for k in MINIMAL_DROP)
                ]
            dumped = yaml.safe_dump(view, allow_unicode=True, sort_keys=False)
            views.append(yaml.safe_load(_adjust_prefix(dumped, name)))
    return views


def _export_yaml_fallback(hass: HomeAssistant, name: str, views: list[dict[str, Any]]) -> str:
    """Scrive il dashboard completo pronto da incollare (piano B)."""
    import yaml

    path = hass.config.path(f"renault-ev-center_{slugify(name)}_dashboard.yaml")
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump({"title": f"{name} EV Center", "views": views}, fh,
                  allow_unicode=True, sort_keys=False)
    return path


async def _notify_fallback(hass: HomeAssistant, name: str, path: str) -> None:
    await hass.services.async_call(
        "persistent_notification", "create",
        {
            "title": "Renault EV Center — Dashboard da creare a mano",
            "message": (
                f"La creazione automatica non è riuscita su questa versione di HA.\n"
                f"1) Impostazioni → Dashboard → Aggiungi dashboard → nome '{name} EV Center'\n"
                f"2) Aprila → matita → ⋮ → 'Modifica configurazione UI in YAML'\n"
                f"3) Incolla il contenuto del file: {path}"
            ),
            "notification_id": f"renault_ev_center_dashboard_{slugify(name)}",
        },
        blocking=False,
    )


async def async_setup_dashboard(hass: HomeAssistant, entry: ConfigEntry, name: str) -> None:
    """Crea (una sola volta) la dashboard laterale con tutte le viste incluse."""
    lovelace_data = hass.data.get("lovelace")
    collection = getattr(lovelace_data, "dashboards", None)
    if collection is None:
        _LOGGER.warning("Lovelace non in modalità storage: uso il piano B")
        wb = bool(entry.data.get('wallbox_enabled', entry.options.get('wallbox_enabled', False)))
        views = await hass.async_add_executor_job(_load_bundled_views, name, wb)
        path = await hass.async_add_executor_job(_export_yaml_fallback, hass, name, views)
        await _notify_fallback(hass, name, path)
        return

    url_path = f"renault-ev-center-{slugify(name)}"

    # già presente? allora solo aggiorna le viste
    già_presente = False
    try:
        for item in collection.async_items():
            if item.get("url_path") == url_path:
                già_presente = True
                break
    except Exception:  # noqa: BLE001
        pass

    wb = bool(entry.data.get("wallbox_enabled", entry.options.get("wallbox_enabled", False)))
    views = await hass.async_add_executor_job(_load_bundled_views, name, wb)
    if not views:
        _LOGGER.warning("Nessuna vista inclusa trovata")
        return

    if not già_presente:
        config = {
            "title": f"{name} EV Center",
            "icon": "mdi:car-electric",
            "url_path": url_path,
            "show_in_sidebar": True,
            "mode": "storage",
        }
        try:
            res = collection.async_create_item(config)
            if res is not None and hasattr(res, "__await__"):
                await res
            _LOGGER.info("Dashboard '%s' creata nella barra laterale", config["title"])
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Creazione dashboard fallita: %s — uso il piano B", err)
            path = await hass.async_add_executor_job(_export_yaml_fallback, hass, name, views)
            await _notify_fallback(hass, name, path)
            return

    # salva le viste nello store della dashboard
    dash_store = None
    for getter in ("async_get_or_create", "async_get", "async_get_item"):
        fn = getattr(collection, getter, None)
        if fn is None:
            continue
        try:
            res = fn(url_path)
            if res is not None and hasattr(res, "__await__"):
                res = await res
            if res is not None and hasattr(res, "async_save"):
                dash_store = res
                break
            if getter == "async_get_item" and res is not None:
                # alcuni build restituiscono la config: prova lo store interno
                inner = getattr(collection, "async_get_or_create", None)
                if inner is not None:
                    dash_store = inner(url_path)
                break
        except Exception:  # noqa: BLE001
            continue

    if dash_store is None or not hasattr(dash_store, "async_save"):
        _LOGGER.error("Store della dashboard non trovato — uso il piano B")
        path = await hass.async_add_executor_job(_export_yaml_fallback, hass, name, views)
        await _notify_fallback(hass, name, path)
        return

    try:
        await dash_store.async_save(views)
        _LOGGER.info("Dashboard '%s': salvate %d viste", f"{name} EV Center", len(views))
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Salvataggio viste fallito: %s — uso il piano B", err)
        path = await hass.async_add_executor_job(_export_yaml_fallback, hass, name, views)
        await _notify_fallback(hass, name, path)
