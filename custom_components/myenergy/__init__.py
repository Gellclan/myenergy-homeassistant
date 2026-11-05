"""myEnergy: sendet Leistung und Verbrauch aus Home Assistant an das eigene myEnergy-Konto (Plan Live)."""
from __future__ import annotations

import logging
import time
from datetime import timedelta

from homeassistant.components.persistent_notification import async_create as notify
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .api import send
from .const import (CONF_KEY, CONF_METER_EXPORT, CONF_METER_IMPORT, CONF_METER_POWER, CONF_PLUGS, DAYS_EVERY_S,
                    INTERVAL_S, NO_PLAN_RETRY_S, STALE_S)
from .logic import Tracker, live_doc, meter_doc, plug_doc, plug_id, to_kwh, to_watt, writes

_LOGGER = logging.getLogger(__name__)
_OFF = ("unavailable", "unknown", "")
# Hinweise in Home Assistant (persistent_notification kennt keine Übersetzungsdateien): Englisch, Deutsch bei deutschem HA
_NOTICE = {
    401: {"en": "The myEnergy pairing key is unknown or revoked. Generate a new one in myEnergy under Settings → Electricity automatically and set up the integration again.",
          "de": "Der Kopplungsschlüssel ist unbekannt oder widerrufen. Erzeuge in myEnergy unter Einstellungen → Strom automatisch einen neuen und richte die Integration neu ein."},
    402: {"en": "Live is not included in your myEnergy plan. As soon as you have Live, the integration sends again (checked hourly).",
          "de": "Live ist in deinem myEnergy-Plan nicht enthalten. Sobald du Live hast, sendet die Integration wieder (stündliche Prüfung)."},
}


def _num(state: State | None) -> float | None:
    if state is None or state.state in _OFF:
        return None
    try:
        return float(state.state)
    except ValueError:
        return None


class Sender:
    """Liest die gewählten Sensoren alle 30 Sekunden; schickt live/ha jedes Mal, den Rest bei Änderung oder alle 15 Minuten."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass, self.entry = hass, entry
        self.tracker = Tracker()
        self.last_days = 0.0
        self.pause_until = 0.0
        self.meter_day: tuple[str, float] | None = None

    def _energy_of(self, ent: er.RegistryEntry | None) -> State | None:
        """Energiezähler desselben Geräts (für kwhTotal und die Tageswerte)."""
        if ent is None or ent.device_id is None:
            return None
        for other in er.async_entries_for_device(er.async_get(self.hass), ent.device_id):
            st = self.hass.states.get(other.entity_id)
            if st is not None and st.attributes.get("device_class") == "energy":
                return st
        return None

    def _plug(self, eid: str, now: float) -> tuple[str, dict, float | None, float | None] | None:
        st = self.hass.states.get(eid)
        if st is None:
            return None
        ent = er.async_get(self.hass).async_get(eid)
        dev = dr.async_get(self.hass).async_get(ent.device_id) if ent and ent.device_id else None
        area_id = (ent.area_id if ent else None) or (dev.area_id if dev else None)
        area = ar.async_get(self.hass).async_get_area(area_id) if area_id else None
        watt = _num(st)
        watt = to_watt(watt, st.attributes.get("unit_of_measurement")) if watt is not None else None
        energy = self._energy_of(ent)
        kwh = _num(energy)
        kwh = to_kwh(kwh, energy.attributes.get("unit_of_measurement")) if kwh is not None and energy else None
        name = (dev.name_by_user or dev.name) if dev and (dev.name_by_user or dev.name) else st.name
        online = st.state not in _OFF and now - st.last_updated.timestamp() < STALE_S
        doc = plug_doc(name, watt, kwh, online, ent.platform if ent else "", area.name if area else None)
        return plug_id(eid), doc, watt, kwh

    def _meter(self, today: str) -> dict | None:
        data = self.entry.data
        if not data.get(CONF_METER_POWER):
            return None
        power_st = self.hass.states.get(data[CONF_METER_POWER])
        power = _num(power_st)
        if power is None:
            return None
        power = to_watt(power, power_st.attributes.get("unit_of_measurement"))

        def kwh(key: str) -> float | None:
            st = self.hass.states.get(data[key]) if data.get(key) else None
            v = _num(st)
            return to_kwh(v, st.attributes.get("unit_of_measurement")) if v is not None else None

        imp, exp = kwh(CONF_METER_IMPORT), kwh(CONF_METER_EXPORT)
        if imp is not None and (self.meter_day is None or self.meter_day[0] != today):
            self.meter_day = (today, imp)
        today_kwh = imp - self.meter_day[1] if imp is not None and self.meter_day else None
        return meter_doc(power, imp, exp, today_kwh, int(power_st.last_updated.timestamp() * 1000))

    async def tick(self, _now=None) -> None:
        now = time.time()
        if now < self.pause_until:
            return
        today = dt_util.now().date().isoformat()
        meter_eid = self.entry.data.get(CONF_METER_POWER)
        plugs: dict[str, dict] = {}
        for eid in self.entry.data.get(CONF_PLUGS, []):
            if eid == meter_eid:
                continue
            hit = self._plug(eid, now)
            if hit:
                pid, doc, watt, kwh = hit
                plugs[pid] = doc
                self.tracker.day(pid, today).add(watt, kwh)
        full = now - self.last_days >= DAYS_EVERY_S
        days = {pid: (today, self.tracker.day(pid, today).doc()) for pid in plugs} if full else None
        changed = plugs if full else self.tracker.changed(plugs)
        meter = self._meter(today)
        events = self.tracker.events(plugs)
        body = writes(live_doc(plugs, meter), changed, days, meter if full else None, events)
        status = await send(self.hass, self.entry.data[CONF_KEY], body)
        if status == 200:
            self.tracker.mark(changed)
            if full:
                self.last_days = now
        elif status in (401, 402):
            self.pause_until = now + NO_PLAN_RETRY_S
            msg = _NOTICE[status]["de" if (self.hass.config.language or "").startswith("de") else "en"]
            notify(self.hass, msg, title="myEnergy", notification_id=f"myenergy_{status}")
            _LOGGER.warning("myEnergy: %s", msg)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    sender = Sender(hass, entry)
    entry.async_on_unload(async_track_time_interval(hass, sender.tick, timedelta(seconds=INTERVAL_S)))
    entry.async_create_background_task(hass, sender.tick(), "myenergy-first")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True
