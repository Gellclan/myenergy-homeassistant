"""Reine Logik der myEnergy-Integration (ohne Home-Assistant-Import, damit sie ohne HA testbar ist).

Schreibt über die Cloud Function `ingest`. Kosten: je Takt (30 s) nur ein Dokument `live/ha` mit allen Leistungen;
plugs/{id} nur bei Änderung (Name, Raum, erreichbar) und alle 15 Minuten, dann auch Tageswerte und devices/hauptzaehler.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

SERVER_TIME = {"__serverTime": True}
SPIKE_W = 200.0
_KEY = re.compile(r"^([A-Za-z0-9]{20,40})\.([A-Za-z0-9_-]{32,64})$")
_ID = re.compile(r"[^A-Za-z0-9_-]+")


def parse_key(key: str) -> tuple[str, str] | None:
    """(uid, geheimnis) wie parseKey in functions/ingest.js, sonst None."""
    m = _KEY.match((key or "").strip())
    return (m.group(1), m.group(2)) if m else None


def plug_id(entity_id: str) -> str:
    """Dokument-ID aus der Leistungs-Entität (sensor.waschmaschine_power -> ha-waschmaschine_power)."""
    return ("ha-" + _ID.sub("_", entity_id.split(".", 1)[-1]))[:80]


def source_of(platform: str) -> str:
    """Herkunft wie im Web (PlugSource): matter, meross, switchbot, sonst other."""
    p = (platform or "").lower()
    if p == "matter":
        return "matter"
    if p.startswith("meross"):
        return "meross"
    if p.startswith("switchbot"):
        return "switchbot"
    return "other"


def to_watt(value: float, unit: str | None) -> float:
    return value * 1000 if (unit or "").lower() == "kw" else value


def to_kwh(value: float, unit: str | None) -> float:
    return value / 1000 if (unit or "").lower() == "wh" else value


def plug_doc(name: str, watt: float | None, kwh_total: float | None, online: bool, platform: str, area: str | None) -> dict:
    doc: dict = {"name": name, "online": online, "source": source_of(platform), "updatedAt": SERVER_TIME}
    if watt is not None:
        doc["watt"] = round(watt, 1)
    if kwh_total is not None:
        doc["kwhTotal"] = round(kwh_total, 3)
    if area:
        doc["area"] = area
    if re.search(r"drucker|printer", name, re.I):
        doc["category"] = "printer"
    return doc


@dataclass
class Day:
    """Tageswerte einer Steckdose; beginnt um Mitternacht neu (Ortszeit von Home Assistant)."""
    date: str
    kwh_start: float | None = None
    kwh_last: float | None = None
    max_w: float = 0.0
    sum_w: float = 0.0
    n: int = 0

    def add(self, watt: float | None, kwh_total: float | None) -> None:
        if watt is not None:
            self.max_w = max(self.max_w, watt)
            self.sum_w += watt
            self.n += 1
        if kwh_total is not None:
            if self.kwh_start is None:
                self.kwh_start = kwh_total
            self.kwh_last = kwh_total

    def doc(self) -> dict:
        """Wie day_doc im Pi-Dienst: fällt der Zählerstand (Neustart der Steckdose), zählt der neue Stand."""
        first, last = self.kwh_start or 0.0, self.kwh_last or 0.0
        kwh = last - first if last >= first else last
        return {"kwh": round(kwh, 3), "maxW": round(self.max_w, 1), "avgW": round(self.sum_w / self.n if self.n else 0.0, 1)}


@dataclass
class Tracker:
    """Merkt sich je Steckdose den Tag und den Zustand für Ereignisse (Spitze, offline, online)."""
    days: dict[str, Day] = field(default_factory=dict)
    state: dict[str, dict] = field(default_factory=dict)

    def day(self, pid: str, today: str) -> Day:
        d = self.days.get(pid)
        if d is None or d.date != today:
            d = self.days[pid] = Day(today)
        return d

    sent: dict[str, dict] = field(default_factory=dict)

    def changed(self, plugs: dict[str, dict]) -> dict[str, dict]:
        """Steckdosen, deren beschreibende Felder sich seit dem letzten Senden geändert haben (Leistung zählt nicht)."""
        return {pid: p for pid, p in plugs.items() if _slow(p) != self.sent.get(pid)}

    def mark(self, plugs: dict[str, dict]) -> None:
        """Nach erfolgreichem Senden merken."""
        self.sent.update({pid: _slow(p) for pid, p in plugs.items()})

    def events(self, plugs: dict[str, dict]) -> list[dict]:
        """Wie detect_events im Pi-Dienst; beim ersten Mal je Steckdose keine Ereignisse. Spitze endet unter 80 %."""
        out: list[dict] = []
        for pid, p in plugs.items():
            watt = float(p.get("watt") or 0)
            was = self.state.get(pid)
            spike = watt >= SPIKE_W or (bool(was and was["spike"]) and watt >= SPIKE_W * 0.8)
            self.state[pid] = {"online": p["online"], "spike": spike}
            if was is None:
                continue
            if was["online"] and not p["online"]:
                out.append({"kind": "offline", "device": p["name"], "text": "nicht mehr erreichbar"})
            elif not was["online"] and p["online"]:
                out.append({"kind": "online", "device": p["name"], "text": "wieder erreichbar"})
            if spike and not was["spike"]:
                out.append({"kind": "spike", "device": p["name"], "text": f"Leistungsspitze {watt:.0f} W"})
        return out


def _slow(p: dict) -> dict:
    return {k: p.get(k) for k in ("name", "online", "source", "area", "category")}


def live_doc(plugs: dict[str, dict], meter: dict | None) -> dict:
    """live/ha: Leistung je erreichbarer Steckdose und die Werte des Hauptzählers, Web und App legen das über plugs/devices."""
    doc: dict = {"plugs": {pid: p["watt"] for pid, p in plugs.items() if p["online"] and "watt" in p}, "updatedAt": SERVER_TIME}
    if meter:
        doc["meter"] = {**meter["values"], "seenAt": meter["seenAt"]}
    return doc


def meter_doc(power_w: float, import_kwh: float | None, export_kwh: float | None, today_kwh: float | None, seen_ms: int) -> dict:
    """devices/hauptzaehler wie device_doc im Pi-Dienst (Leistung = Bezug minus Einspeisung)."""
    values: dict = {"power": round(power_w, 1)}
    if import_kwh is not None:
        values["importKwh"] = round(import_kwh, 3)
    if export_kwh is not None:
        values["exportKwh"] = round(export_kwh, 3)
    if today_kwh is not None:
        values["todayKwh"] = round(today_kwh, 3)
    return {"name": "Hauptzähler", "kind": "meter", "source": "smartmeter", "values": values, "seenAt": seen_ms, "updatedAt": SERVER_TIME}


def writes(live: dict, plugs: dict[str, dict], days: dict[str, tuple[str, dict]] | None, meter: dict | None, events: list[dict]) -> list[dict]:
    """Schreibaufträge für ingest: immer live/ha, dazu nur die übergebenen Steckdosen; days und meter nur alle 15 Minuten."""
    out = [{"op": "set", "path": "live/ha", "data": live}]
    out += [{"op": "set", "path": f"plugs/{pid}", "data": doc} for pid, doc in plugs.items()]
    for pid, (date, doc) in (days or {}).items():
        out.append({"op": "set", "path": f"plugs/{pid}/days/{date}", "data": doc})
    if meter:
        out.append({"op": "set", "path": "devices/hauptzaehler", "data": meter})
    out += [{"op": "add", "path": "events", "data": {**e, "t": SERVER_TIME}} for e in events]
    return out
