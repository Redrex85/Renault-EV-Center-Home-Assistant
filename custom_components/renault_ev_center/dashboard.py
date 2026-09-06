"""Creazione automatica della dashboard laterale e della foto dell'auto."""
from __future__ import annotations

import logging
import os
import re
import shutil
from typing import Any

from homeassistant.components import frontend
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


def _get_dashboards(hass: HomeAssistant):
    """Registro dashboard: dict {url_path: LovelaceStorage} (HA nuova) o collection (HA vecchia)."""
    lovelace_data = hass.data.get("lovelace")
    return getattr(lovelace_data, "dashboards", None) if lovelace_data is not None else None


async def _create_new_api(hass: HomeAssistant, dashboards: dict, url_path: str, title: str):
    """HA ≥ 2025.9: crea la voce dashboard e registra panel + store in memoria.

    ponytail: la collection di lovelace non è esposta in hass.data, quindi si
    usa un'istanza propria che scrive .storage/lovelace_dashboards; se l'utente
    modifica altre dashboard nella stessa sessione il save di quella collection
    può scartare la voce — al riavvio di HA il pannello ricompare.
    """
    try:
        from homeassistant.components.lovelace.dashboard import (
            DashboardsCollection,
            LovelaceStorage,
        )
    except ImportError:  # struttura moduli diversa in altre versioni HA
        _LOGGER.warning("Modulo lovelace.dashboard non disponibile: uso il piano B")
        return None
    try:
        coll = DashboardsCollection(hass)
        await coll.async_load()
        item = await coll.async_create_item(
            {
                "title": title,
                "icon": "mdi:car-electric",
                "url_path": url_path,
                "show_in_sidebar": True,
            }
        )
        store = LovelaceStorage(hass, dict(item))
        if not frontend.async_panel_exists(hass, url_path):
            frontend.async_register_built_in_panel(
                hass,
                "lovelace",
                sidebar_title=title,
                sidebar_icon="mdi:car-electric",
                frontend_url_path=url_path,
                show_in_sidebar=True,
            )
        dashboards[url_path] = store
        _LOGGER.info("Dashboard '%s' creata nella barra laterale", title)
        return store
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Creazione dashboard fallita: %s — uso il piano B", err)
        return None


async def async_setup_dashboard(hass: HomeAssistant, entry: ConfigEntry, name: str) -> None:
    """Crea (una sola volta) la dashboard laterale con tutte le viste incluse."""
    url_path = f"renault-ev-center-{slugify(name)}"
    title = f"{name} EV Center"
    wb = bool(entry.data.get("wallbox_enabled", entry.options.get("wallbox_enabled", False)))
    views = await hass.async_add_executor_job(_load_bundled_views, name, wb)
    if not views:
        _LOGGER.warning("Nessuna vista inclusa trovata")
        return

    async def piano_b() -> None:
        path = await hass.async_add_executor_job(_export_yaml_fallback, hass, name, views)
        await _notify_fallback(hass, name, path)

    dashboards = _get_dashboards(hass)
    if dashboards is None:
        _LOGGER.warning("Lovelace non in modalità storage: uso il piano B")
        await piano_b()
        return

    store = None
    if isinstance(dashboards, dict):
        # HA ≥ 2025.9: {url_path: LovelaceStorage} già popolato al boot
        store = dashboards.get(url_path)
        if store is None:
            store = await _create_new_api(hass, dashboards, url_path, title)
    elif hasattr(dashboards, "async_create_item"):
        # HA vecchie: DashboardsCollection, listener ufficiale registra il panel
        già_presente = False
        try:
            for item in dashboards.async_items():
                if item.get("url_path") == url_path:
                    già_presente = True
                    break
        except Exception:  # noqa: BLE001
            pass
        if not già_presente:
            try:
                res = dashboards.async_create_item(
                    {
                        "title": title,
                        "icon": "mdi:car-electric",
                        "url_path": url_path,
                        "show_in_sidebar": True,
                        "mode": "storage",
                    }
                )
                if hasattr(res, "__await__"):
                    await res
                _LOGGER.info("Dashboard '%s' creata nella barra laterale", title)
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Creazione dashboard fallita: %s — uso il piano B", err)
                await piano_b()
                return
        for getter in ("async_get_or_create", "async_get", "async_get_item"):
            fn = getattr(dashboards, getter, None)
            if fn is None:
                continue
            try:
                res = fn(url_path)
                if hasattr(res, "__await__"):
                    res = await res
                if res is not None and hasattr(res, "async_save"):
                    store = res
                    break
            except Exception:  # noqa: BLE001
                continue

    if store is None or not hasattr(store, "async_save"):
        _LOGGER.error("Store della dashboard non trovato — uso il piano B")
        await piano_b()
        return

    try:
        await store.async_save({"views": views})
        _LOGGER.info("Dashboard '%s': salvate %d viste", title, len(views))
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Salvataggio viste fallito: %s — uso il piano B", err)
        await piano_b()


async def async_remove_dashboard(hass: HomeAssistant, name: str) -> None:
    """Rimuove la dashboard laterale creata dall'integrazione."""
    url_path = f"renault-ev-center-{slugify(name)}"
    dashboards = _get_dashboards(hass)
    if dashboards is None:
        return

    if isinstance(dashboards, dict):
        # HA ≥ 2025.9: dict {url_path: LovelaceStorage}
        store = dashboards.pop(url_path, None)
        if store is not None:
            try:
                await store.async_delete()
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Rimozione store dashboard fallita: %s", err)
            try:
                frontend.async_remove_panel(hass, url_path, warn_if_unknown=False)
            except TypeError:  # signature senza warn_if_unknown
                frontend.async_remove_panel(hass, url_path)
            _LOGGER.info("Dashboard '%s' rimossa", url_path)
        try:
            from homeassistant.components.lovelace.dashboard import DashboardsCollection
            coll = DashboardsCollection(hass)
            await coll.async_load()
            for iid, it in list(coll.data.items()):
                if it.get("url_path") == url_path:
                    await coll.async_delete_item(iid)
                    break
        except ImportError:
            pass
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Rimozione voce da lovelace_dashboards fallita: %s", err)
        return

    if hasattr(dashboards, "async_delete_item"):
        # HA vecchie: collection con listener ufficiale
        try:
            for item in list(dashboards.async_items()):
                if item.get("url_path") == url_path:
                    res = dashboards.async_delete_item(item["id"])
                    if hasattr(res, "__await__"):
                        await res
                    break
            frontend.async_remove_panel(hass, url_path)
            _LOGGER.info("Dashboard '%s' rimossa", url_path)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Rimozione dashboard fallita: %s", err)
