"""Einrichtung und Senden in einem echten Home Assistant (Testumgebung).

Aufruf: pip install pytest-homeassistant-custom-component (Python >= 3.12), dann im Ordner ha-integration: pytest tests/ha_flow_test.py
"""
from homeassistant.core import HomeAssistant

from custom_components.myenergy.const import DOMAIN, INGEST_URL

KEY = "a" * 28 + "." + "b" * 40


def _states(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.herd_power", "250", {"device_class": "power", "unit_of_measurement": "W", "friendly_name": "Herd Leistung"})
    hass.states.async_set("sensor.zaehler_power", "1.2", {"device_class": "power", "unit_of_measurement": "kW"})
    hass.states.async_set("sensor.zaehler_import", "1500", {"device_class": "energy", "unit_of_measurement": "kWh"})


async def test_einrichten_und_senden(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(INGEST_URL, json={"ok": True})
    _states(hass)
    flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    r = await hass.config_entries.flow.async_configure(flow["flow_id"], {"key": "falsch"})
    assert r["errors"] == {"base": "invalid_key"}
    r = await hass.config_entries.flow.async_configure(flow["flow_id"], {"key": KEY})
    assert r["step_id"] == "select"
    assert aioclient_mock.mock_calls[0][2] == {"ping": True}
    assert aioclient_mock.mock_calls[0][3]["Authorization"] == f"Bearer {KEY}"
    r = await hass.config_entries.flow.async_configure(flow["flow_id"], {
        "plugs": ["sensor.herd_power", "sensor.zaehler_power"], "meter_power": "sensor.zaehler_power", "meter_import": "sensor.zaehler_import"})
    assert r["type"] == "create_entry"
    await hass.async_block_till_done()

    body = aioclient_mock.mock_calls[-1][2]
    by_path = {w["path"]: w for w in body["writes"]}
    assert "plugs/ha-zaehler_power" not in by_path, "Smart Meter ist keine Steckdose"
    plug = by_path["plugs/ha-herd_power"]["data"]
    assert plug["watt"] == 250 and plug["online"] is True and plug["name"] == "Herd Leistung"
    assert by_path["plugs/ha-herd_power/days/" + next(p.split("/")[-1] for p in by_path if "/days/" in p)]["data"]["maxW"] == 250
    meter = by_path["devices/hauptzaehler"]["data"]
    assert meter["values"] == {"power": 1200, "importKwh": 1500, "todayKwh": 0}
    assert by_path["live/ha"]["data"]["plugs"] == {"ha-herd_power": 250}

    # nächster Takt ohne Änderung: nur live/ha (ein Schreibvorgang statt einer je Steckdose)
    from datetime import timedelta
    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed
    hass.states.async_set("sensor.herd_power", "260", {"device_class": "power", "unit_of_measurement": "W", "friendly_name": "Herd Leistung"})
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()
    body = aioclient_mock.mock_calls[-1][2]
    assert [w["path"] for w in body["writes"]] == ["live/ha"]
    assert body["writes"][0]["data"]["plugs"] == {"ha-herd_power": 260}


async def test_ohne_plan_live(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(INGEST_URL, status=402, json={"error": "Live ist nicht freigeschaltet"})
    flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    r = await hass.config_entries.flow.async_configure(flow["flow_id"], {"key": KEY})
    assert r["errors"] == {"base": "no_plan"}


async def test_geraet_mit_raum_und_energiezaehler(hass: HomeAssistant, aioclient_mock) -> None:
    from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    aioclient_mock.post(INGEST_URL, json={"ok": True})
    matter = MockConfigEntry(domain="matter")
    matter.add_to_hass(hass)
    kueche = ar.async_get(hass).async_create("Küche")
    devs = dr.async_get(hass)
    dev = devs.async_get_or_create(config_entry_id=matter.entry_id, identifiers={("matter", "k1")}, name="Kühlschrank")
    devs.async_update_device(dev.id, area_id=kueche.id)
    reg = er.async_get(hass)
    power = reg.async_get_or_create("sensor", "matter", "k1-p", device_id=dev.id)
    energy = reg.async_get_or_create("sensor", "matter", "k1-e", device_id=dev.id)
    hass.states.async_set(power.entity_id, "78", {"device_class": "power", "unit_of_measurement": "W"})
    hass.states.async_set(energy.entity_id, "1200", {"device_class": "energy", "unit_of_measurement": "Wh"})

    entry = MockConfigEntry(domain=DOMAIN, data={"key": KEY, "plugs": [power.entity_id]})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    plug = next(w["data"] for w in aioclient_mock.mock_calls[-1][2]["writes"] if w["path"].startswith("plugs/") and "/days/" not in w["path"])
    assert (plug["name"], plug["area"], plug["source"], plug["kwhTotal"], plug["watt"]) == ("Kühlschrank", "Küche", "matter", 1.2, 78)
