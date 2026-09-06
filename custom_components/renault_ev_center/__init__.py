"""Renault EV Center: statistiche viaggi/ricariche per Renault elettriche via entità esistenti."""
from __future__ import annotations

import logging
from datetime import datetime as dt

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import CONF_CREATE_DASHBOARD, CONF_NAME, DOMAIN, PLATFORMS
from .coordinator import RenaultMateCoordinator
from .dashboard import async_setup_dashboard, setup_card_js, setup_car_image

_LOGGER = logging.getLogger(__name__)

SERVICE_CLOSE_TRIP = "close_trip"
SERVICE_RESET_COUNTERS = "reset_counters"
SERVICE_EXPORT_CSV = "export_trips_csv"
SERVICE_ADD_CHARGE = "add_manual_charge"
SERVICE_DELETE_TRIP = "delete_trip"
SERVICE_ADD_MAINTENANCE = "add_maintenance"
SERVICE_DELETE_MAINTENANCE = "delete_maintenance"
SERVICE_RENEW_INSURANCE = "renew_insurance"
SERVICE_SET_SCADENZA = "set_scadenza"
SERVICE_SET_TAGLIANDO = "set_tagliando"
SERVICE_CREATE_DASHBOARD = "create_dashboard"

RESET_SCOPES = ["km", "energia", "costi", "viaggi", "ricariche", "all"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura l'entry: crea il coordinator e le piattaforme."""
    hass.data.setdefault(DOMAIN, {})
    coordinator = RenaultMateCoordinator(hass, entry)
    opts = {**entry.data, **entry.options}
    try:
        await coordinator.async_load_store()
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady(f"Impossibile leggere lo storage: {err}") from err

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # foto del modello + dashboard automatica nella barra laterale
    if opts.get(CONF_CREATE_DASHBOARD, True):
        try:
            await async_setup_dashboard(hass, entry, str(opts.get(CONF_NAME, "Renault")))
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Dashboard automatica non creata: %s", err)
    try:
        await hass.async_add_executor_job(setup_car_image, hass, entry)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Immagine auto non copiata: %s", err)
    try:
        await hass.async_add_executor_job(setup_card_js, hass)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Card non copiata: %s", err)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # ---------------------------------------------------------------- servizi
    # Handlers (definiti una sola volta, usano _all_coordinators per multi-entry)
    async def handle_close_trip(call: ServiceCall) -> None:
        for coord in _all_coordinators(hass):
            rec = coord.service_close_trip()
            if rec:
                _LOGGER.info("Viaggio chiuso manualmente: %s km", rec.get("km"))

    async def handle_reset_counters(call: ServiceCall) -> None:
        scope = call.data.get("scope", "all")
        for coord in _all_coordinators(hass):
            coord.service_reset_counters(scope)

    async def handle_export_csv(call: ServiceCall) -> dict:
        paths = []
        for coord in _all_coordinators(hass):
            paths.append(await coord.service_export_csv())
        _LOGGER.info("Export CSV completato: %s", ", ".join(paths))
        return {"paths": paths}

    async def handle_add_charge(call: ServiceCall) -> None:
        kwh = float(call.data["kwh"])
        costo = float(call.data.get("costo", 0))
        tipo = call.data.get("tipo", "Pubblica")
        quando_raw = call.data.get("quando")
        quando = dt_util.parse_datetime(quando_raw) if quando_raw else dt_util.now()
        if isinstance(quando, dt) and quando.tzinfo is None:
            quando = quando.replace(tzinfo=dt_util.UTC)
        for coord in _all_coordinators(hass):
            rec = coord.service_add_manual_charge(kwh, costo, tipo, quando)
            _LOGGER.info("Ricarica manuale aggiunta: %s kWh (%s)", rec["kwh"], rec["tipo"])

    async def handle_delete_trip(call: ServiceCall) -> None:
        trip_id = int(call.data["trip_id"])
        for coord in _all_coordinators(hass):
            coord.service_delete_trip(trip_id)

    async def handle_add_maintenance(call: ServiceCall) -> None:
        for coord in _all_coordinators(hass):
            rec = coord.service_add_maintenance(
                call.data["data"],
                float(call.data["km"]),
                float(call.data.get("costo", 0)),
                call.data.get("tipo", "Tagliando"),
                call.data.get("note", ""),
            )
            _LOGGER.info("Tagliando registrato: %s (%s km)", rec["data"], rec["km"])

    async def handle_delete_maintenance(call: ServiceCall) -> None:
        mid = int(call.data["maintenance_id"])
        for coord in _all_coordinators(hass):
            coord.service_delete_maintenance(mid)

    async def handle_renew_insurance(call: ServiceCall) -> None:
        mesi = int(call.data.get("mesi", 12))
        data = str(call.data.get("data", "") or "")
        for coord in _all_coordinators(hass):
            nuova = coord.service_renew_insurance(mesi, data)
            _LOGGER.info("Assicurazione rinnovata fino al %s", nuova)

    async def handle_set_scadenza(call: ServiceCall) -> None:
        for coord in _all_coordinators(hass):
            coord.service_set_scadenza(call.data["nome"], call.data["data"])

    async def handle_set_tagliando(call: ServiceCall) -> None:
        for coord in _all_coordinators(hass):
            coord.service_set_tagliando(call.data["mode"], str(call.data["valore"]))

    async def handle_create_dashboard(call: ServiceCall) -> None:
        for coord in _all_coordinators(hass):
            await async_setup_dashboard(hass, coord.entry, str(coord.opts.get(CONF_NAME, "Renault")))

    def _register(name, handler, schema=None, supports_response=None):
        if hass.services.has_service(DOMAIN, name):
            return
        kwargs: dict = {}
        if schema is not None:
            kwargs["schema"] = schema
        if supports_response is not None:
            kwargs["supports_response"] = supports_response
        hass.services.async_register(DOMAIN, name, handler, **kwargs)

    _register(SERVICE_CLOSE_TRIP, handle_close_trip)
    _register(SERVICE_RESET_COUNTERS, handle_reset_counters,
              schema=vol.Schema({vol.Optional("scope", default="all"): vol.In(RESET_SCOPES)}))
    _register(SERVICE_EXPORT_CSV, handle_export_csv,
              supports_response=SupportsResponse.OPTIONAL)
    _register(SERVICE_ADD_CHARGE, handle_add_charge,
              schema=vol.Schema({
                  vol.Required("kwh"): cv.positive_float,
                  vol.Optional("costo", default=0.0): vol.Coerce(float),
                  vol.Optional("tipo", default="Pubblica"): str,
                  vol.Optional("quando"): str,
              }))
    _register(SERVICE_DELETE_TRIP, handle_delete_trip,
              schema=vol.Schema({vol.Required("trip_id"): cv.positive_int}))
    _register(SERVICE_ADD_MAINTENANCE, handle_add_maintenance,
              schema=vol.Schema({
                  vol.Required("data"): str,
                  vol.Required("km"): cv.positive_float,
                  vol.Optional("costo", default=0.0): vol.Coerce(float),
                  vol.Optional("tipo", default="Tagliando"): str,
                  vol.Optional("note", default=""): str,
              }))
    _register(SERVICE_DELETE_MAINTENANCE, handle_delete_maintenance,
              schema=vol.Schema({vol.Required("maintenance_id"): cv.positive_int}))
    _register(SERVICE_RENEW_INSURANCE, handle_renew_insurance,
              schema=vol.Schema({
                  vol.Optional("mesi", default=12): vol.All(vol.Coerce(int), vol.In([6, 12])),
                  vol.Optional("data", default=""): str,
              }))
    _register(SERVICE_SET_SCADENZA, handle_set_scadenza,
              schema=vol.Schema({
                  vol.Required("nome"): vol.In(["assicurazione", "bollo", "revisione", "tagliando_data"]),
                  vol.Required("data"): str,
              }))
    _register(SERVICE_SET_TAGLIANDO, handle_set_tagliando,
              schema=vol.Schema({
                  vol.Required("mode"): vol.In(["km", "data"]),
                  vol.Required("valore"): str,
              }))
    _register(SERVICE_CREATE_DASHBOARD, handle_create_dashboard)

    return True


def _all_coordinators(hass: HomeAssistant) -> list[RenaultMateCoordinator]:
    return list(hass.data.get(DOMAIN, {}).values())


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
