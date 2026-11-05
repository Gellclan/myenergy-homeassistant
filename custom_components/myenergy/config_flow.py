"""Einrichtung: Kopplungsschlüssel aus der myEnergy-App einfügen, dann wählen, was gesendet wird."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .api import post
from .const import CONF_KEY, CONF_METER_EXPORT, CONF_METER_IMPORT, CONF_METER_POWER, CONF_PLUGS, DOMAIN
from .logic import parse_key

_POWER = EntitySelectorConfig(domain="sensor", device_class="power")
_ENERGY = EntitySelectorConfig(domain="sensor", device_class="energy")


class MyEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _key = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            key = user_input[CONF_KEY].strip()
            parsed = parse_key(key)
            if not parsed:
                errors["base"] = "invalid_key"
            else:
                status = await post(self.hass, key, {"ping": True})
                errors_by_status = {401: "unknown_key", 402: "no_plan"}
                if status != 200:
                    errors["base"] = errors_by_status.get(status, "cannot_connect")
                else:
                    await self.async_set_unique_id(parsed[0])
                    self._abort_if_unique_id_configured()
                    self._key = key
                    return await self.async_step_select()
        return self.async_show_form(step_id="user", data_schema=vol.Schema({vol.Required(CONF_KEY): str}), errors=errors)

    async def async_step_select(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="myEnergy", data={CONF_KEY: self._key, **user_input})
        # vorgewählt: alles, was Strom misst
        power = [s.entity_id for s in self.hass.states.async_all("sensor") if s.attributes.get("device_class") == "power"]
        schema = vol.Schema({
            vol.Optional(CONF_PLUGS, default=power): EntitySelector(EntitySelectorConfig(domain="sensor", device_class="power", multiple=True)),
            vol.Optional(CONF_METER_POWER): EntitySelector(_POWER),
            vol.Optional(CONF_METER_IMPORT): EntitySelector(_ENERGY),
            vol.Optional(CONF_METER_EXPORT): EntitySelector(_ENERGY),
        })
        # shortcut: Auswahl ändern nur über Entfernen und neu Hinzufügen; Optionsdialog, sobald Kunden danach fragen
        return self.async_show_form(step_id="select", data_schema=schema)
