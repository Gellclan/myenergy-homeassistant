# myEnergy für Home Assistant

Schickt Leistung und Verbrauch deiner Steckdosen und deines Smart Meters aus Home Assistant an dein myEnergy-Konto
(Plan Live). Gesendet werden nur Leistung, Energie, Raum und Name, nichts anderes.

## Installation

1. HACS → Integrationen → ⋮ → Benutzerdefinierte Repositories → dieses Repository, Kategorie „Integration“ → myEnergy installieren.
   Ohne HACS: Ordner `custom_components/myenergy` nach `config/custom_components/` kopieren.
2. Home Assistant neu starten.
3. In myEnergy: Einstellungen → Strom automatisch → „Schlüssel erzeugen“, Schlüssel kopieren.
4. Home Assistant: Einstellungen → Geräte & Dienste → Integration hinzufügen → myEnergy → Schlüssel einfügen,
   dann die Steckdosen und (falls vorhanden) die Sensoren des Smart Meters wählen.

Nach etwa einer Minute erscheinen die Geräte in myEnergy unter Live.

## Entwicklung

Reine Logik in `custom_components/myenergy/logic.py`, Tests: `python3 -m unittest discover -s tests`.
Die Felder entsprechen `pi-dienst/live.py` (plugs, plugs/*/days, devices/hauptzaehler, events), geschrieben über die Cloud Function `ingest`.
