"""Tests der reinen Logik: cd ha-integration && python3 -m unittest discover -s tests"""
import importlib.util
import pathlib
import sys
import unittest

# logic.py direkt laden, ohne das Paket (dessen __init__ braucht Home Assistant)
_spec = importlib.util.spec_from_file_location("logic", pathlib.Path(__file__).parents[1] / "custom_components/myenergy/logic.py")
logic = sys.modules["logic"] = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(logic)


class LogicTest(unittest.TestCase):
    def test_key_wie_ingest(self):
        self.assertEqual(logic.parse_key(" " + "a" * 28 + "." + "b" * 40 + " "), ("a" * 28, "b" * 40))
        self.assertIsNone(logic.parse_key("ohne-punkt"))
        self.assertIsNone(logic.parse_key("a" * 28 + "." + "kurz"))

    def test_ids_und_herkunft(self):
        self.assertEqual(logic.plug_id("sensor.waschmaschine_power"), "ha-waschmaschine_power")
        self.assertEqual(logic.plug_id("sensor.küche:licht"), "ha-k_che_licht")
        self.assertTrue(len(logic.plug_id("sensor." + "x" * 200)) <= 80)
        self.assertEqual(logic.source_of("matter"), "matter")
        self.assertEqual(logic.source_of("meross_lan"), "meross")
        self.assertEqual(logic.source_of("shelly"), "other")

    def test_einheiten(self):
        self.assertEqual(logic.to_watt(1.2, "kW"), 1200)
        self.assertEqual(logic.to_kwh(1500, "Wh"), 1.5)

    def test_steckdose(self):
        doc = logic.plug_doc("3D-Drucker", 142.04, 12.3456, True, "matter", "Büro")
        self.assertEqual(doc["watt"], 142.0)
        self.assertEqual(doc["kwhTotal"], 12.346)
        self.assertEqual(doc["category"], "printer")
        self.assertEqual(doc["area"], "Büro")
        self.assertEqual(doc["updatedAt"], logic.SERVER_TIME)

    def test_tag_und_neustart(self):
        t = logic.Tracker()
        d = t.day("p", "2026-11-05")
        d.add(100, 10.0)
        d.add(300, 10.5)
        self.assertEqual(d.doc(), {"kwh": 0.5, "maxW": 300, "avgW": 200})
        d.add(0, 0.2)  # Steckdose neu gestartet, Zähler bei 0
        self.assertEqual(d.doc()["kwh"], 0.2)
        self.assertIsNot(t.day("p", "2026-11-06"), d, "um Mitternacht neu")

    def test_ereignisse(self):
        t = logic.Tracker()
        p = {"name": "Herd", "online": True, "watt": 10}
        self.assertEqual(t.events({"h": p}), [], "erstes Mal still")
        self.assertEqual([e["kind"] for e in t.events({"h": {**p, "watt": 250}})], ["spike"])
        self.assertEqual(t.events({"h": {**p, "watt": 170}}), [], "Spitze hält bis unter 80 %")
        self.assertEqual([e["kind"] for e in t.events({"h": {**p, "online": False, "watt": 0}})], ["offline"])

    def test_schreibauftraege(self):
        meter = logic.meter_doc(-300, 1.0, 2.0, None, 5)
        live = logic.live_doc({"p": {"name": "a", "online": True, "watt": 7}, "q": {"name": "b", "online": False, "watt": 0}}, meter)
        self.assertEqual(live["plugs"], {"p": 7}, "nur erreichbare Steckdosen")
        self.assertEqual(live["meter"], {"power": -300, "importKwh": 1.0, "exportKwh": 2.0, "seenAt": 5})
        w = logic.writes(live, {"p": {"name": "a"}}, {"p": ("2026-11-05", {"kwh": 1})}, meter, [{"kind": "spike"}])
        self.assertEqual([x["path"] for x in w], ["live/ha", "plugs/p", "plugs/p/days/2026-11-05", "devices/hauptzaehler", "events"])
        self.assertEqual(w[4]["op"], "add")
        self.assertEqual([x["path"] for x in logic.writes(live, {}, None, None, [])], ["live/ha"], "ohne Änderung nur ein Dokument")

    def test_nur_aenderungen(self):
        t = logic.Tracker()
        p = {"name": "Herd", "online": True, "source": "matter", "watt": 10}
        self.assertEqual(list(t.changed({"h": p})), ["h"], "neu")
        t.mark({"h": p})
        self.assertEqual(t.changed({"h": {**p, "watt": 999, "kwhTotal": 5}}), {}, "Leistung und kWh allein schreiben nicht")
        self.assertEqual(list(t.changed({"h": {**p, "online": False}})), ["h"])
        self.assertEqual(list(t.changed({"h": {**p, "area": "Küche"}})), ["h"])


if __name__ == "__main__":
    unittest.main()
