# myEnergy für Home Assistant

**Deutsch** · [English](#english)

Schickt Leistung und Verbrauch deiner Steckdosen und deines Smart Meters aus Home Assistant an dein
[myEnergy](https://myenergy-63712.web.app)-Konto. Dort siehst du Live-Werte, Statistik und Kosten je Gerät und Raum.

- **Du brauchst:** Home Assistant, das rund um die Uhr läuft (z. B. Raspberry Pi 4/5), Steckdosen mit Strommessung
  (Matter, Shelly, Meross, SwitchBot …) oder einen Lesekopf am Smart Meter, und ein myEnergy-Konto mit Plan **Live**.
- **Gesendet werden nur** Leistung, Energie, Name und Raum der gewählten Sensoren. Keine Kameras, Schlösser, Standorte.
- Hardware verkaufen wir nicht.

## Installation

1. HACS → Integrationen → ⋮ → **Benutzerdefinierte Repositories** → `https://github.com/Gellclan/myenergy-homeassistant`, Kategorie **Integration** → myEnergy herunterladen.
   Ohne HACS: Ordner `custom_components/myenergy` nach `config/custom_components/` kopieren.
2. Home Assistant neu starten.
3. In myEnergy: **Einstellungen → Strom automatisch → Schlüssel erzeugen**, Schlüssel kopieren.
4. Home Assistant: **Einstellungen → Geräte & Dienste → Integration hinzufügen → myEnergy** → Schlüssel einfügen,
   Steckdosen und (falls vorhanden) die Sensoren des Smart Meters wählen.

Nach etwa einer Minute erscheinen die Geräte in myEnergy unter **Live**. Hilfe: [myEnergy-Hilfe](https://myenergy-63712.web.app/hilfe#live), support@gellclan.at.

---

<a id="english"></a>
# myEnergy for Home Assistant

Sends power and energy of your plugs and smart meter from Home Assistant to your [myEnergy](https://myenergy-63712.web.app)
account, where you see live values, statistics and cost per device and room.

- **You need:** Home Assistant running around the clock (e.g. Raspberry Pi 4/5), plugs that measure power
  (Matter, Shelly, Meross, SwitchBot …) or a reader on the smart meter, and a myEnergy account with the **Live** plan.
- **Only** power, energy, name and room of the selected sensors are sent.
- We don't sell hardware.

## Installation

1. HACS → Integrations → ⋮ → **Custom repositories** → `https://github.com/Gellclan/myenergy-homeassistant`, category **Integration** → download myEnergy.
   Without HACS: copy `custom_components/myenergy` to `config/custom_components/`.
2. Restart Home Assistant.
3. In myEnergy: **Settings → Electricity automatically → Generate key**, copy the key.
4. Home Assistant: **Settings → Devices & services → Add integration → myEnergy** → paste the key, choose plugs and smart meter sensors.

After about a minute the devices appear in myEnergy under **Live**. Help: support@gellclan.at.

## Lizenz / License

Alle Rechte vorbehalten / All rights reserved, see [LICENSE](LICENSE).

## Entwicklung / Development

Quelle ist der Ordner `ha-integration/` im myEnergy-Repository; dieses Repository entsteht daraus mit
`git subtree split --prefix ha-integration`. Tests: `python3 -m unittest discover -s tests` (Logik) und `pytest` mit
`pytest-homeassistant-custom-component` (Python ≥ 3.12).
