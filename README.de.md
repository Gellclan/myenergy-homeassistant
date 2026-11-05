# myEnergy für Home Assistant

[English](README.md) (ausführliche Anleitung, Fehlerbilder, Datenschutz)

Schickt Leistung und Verbrauch deiner Steckdosen und deines Smart Meters aus Home Assistant an dein
[myEnergy](https://myenergy-63712.web.app)-Konto.

**Du brauchst:** Home Assistant, das rund um die Uhr läuft (z. B. Raspberry Pi 4/5), Steckdosen mit Strommessung
oder einen Lesekopf am Smart Meter (schon in Home Assistant eingebunden) und ein myEnergy-Konto mit Plan **Live**.
Hardware verkaufen wir nicht.

1. **HACS** → ⋮ → **Benutzerdefinierte Repositories** → `https://github.com/Gellclan/myenergy-homeassistant`, Typ **Integration** → myEnergy herunterladen → Home Assistant neu starten.
2. In myEnergy: **Einstellungen → Strom automatisch → Schlüssel erzeugen**, Schlüssel kopieren.
3. Home Assistant: **Einstellungen → Geräte & Dienste → Integration hinzufügen → myEnergy** → Schlüssel einfügen, Steckdosen und Smart Meter wählen.

Nach etwa einer Minute erscheinen die Geräte in myEnergy unter **Live**. Gesendet werden nur Name, Leistung, Energie,
Erreichbarkeit und Raum der gewählten Sensoren. Hilfe: [myEnergy-Hilfe](https://myenergy-63712.web.app/hilfe#live), support@gellclan.at.
