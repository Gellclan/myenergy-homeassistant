# myEnergy for Home Assistant

[Deutsche Anleitung](README.de.md)

Sends power and energy of your plugs and your smart meter from Home Assistant to your
[myEnergy](https://myenergy-63712.web.app) account. In myEnergy you then see live values, statistics and cost per
device and room, events such as power peaks or devices going offline, and your household consumption right now.

## What you need

- **Home Assistant running around the clock** (e.g. on a Raspberry Pi 4 or 5 or a Home Assistant Green) with internet access.
- **Devices that measure power, already added to Home Assistant:** smart plugs (Matter, Shelly, Meross, SwitchBot …)
  and/or a reader on your smart meter. Anything that shows up in Home Assistant as a power sensor (W or kW) works;
  if the same device also has an energy sensor (kWh or Wh), myEnergy uses it for daily consumption.
- **A myEnergy account with the Live plan.** The integration is included in Live. We don't sell hardware.
- [HACS](https://hacs.xyz) to install and update the integration (recommended), or file access to your Home Assistant configuration.

## Installation

### With HACS (recommended)

1. In Home Assistant open **HACS** → ⋮ (top right) → **Custom repositories**.
2. Repository: `https://github.com/Gellclan/myenergy-homeassistant`, type: **Integration** → **Add**.
3. Search for **myEnergy** in HACS → **Download**.
4. Restart Home Assistant (**Settings → System → Restart**).

Updates then appear in HACS like for any other integration.

### Without HACS

Copy the folder `custom_components/myenergy` from this repository to `config/custom_components/myenergy` in your
Home Assistant configuration and restart Home Assistant.

## Setup

1. **Get your pairing key in myEnergy:** web or app → **Settings → Electricity automatically** (German: „Strom automatisch“)
   → **Generate key** → copy it. The key is shown only once; treat it like a password.
2. **Add the integration in Home Assistant:** **Settings → Devices & services → Add integration → myEnergy** → paste the key.
3. **Choose what myEnergy should see:**
   - *Plugs and devices that measure power* – pre-selected: every power sensor. Untick what you don't want.
   - *Smart meter: power* (optional) – the live power of your main meter (import minus export).
   - *Smart meter: energy imported / exported* (optional) – meter readings in kWh, used for "today".
4. After about a minute the devices appear in myEnergy under **Live**, grouped by the rooms (areas) you set in
   Home Assistant. Daily values follow every 5 minutes.

To change the selection later, remove the integration and add it again with the same key.

## What is sent

Every 30 seconds, only for the sensors you selected: name, power, energy counter, online state and room (area).
Every 5 minutes the day's consumption, peak and average per device. Nothing else: no cameras, locks, locations,
presence or other entities. Data goes encrypted (HTTPS) to the myEnergy cloud (Google Firebase, region europe-west1)
and only into your own account. Details: [privacy policy](https://myenergy-63712.web.app/datenschutz).

## Troubleshooting

| Message / symptom | What to do |
|---|---|
| *The key has the wrong format* | Copy the whole key again from myEnergy (it looks like `abc…xyz.abc…xyz`, no spaces). |
| *Key unknown or revoked* | A newer key was generated or the key was revoked. Generate a new one in myEnergy and set up the integration again. |
| *Live is not included in your myEnergy plan* | Choose the Live plan in myEnergy (**Settings → Plan**). The integration then sends again (it checks hourly). |
| *myEnergy cannot be reached* | Check the internet connection of Home Assistant. |
| Notification "myEnergy" in Home Assistant | Same as above: key revoked (401) or plan without Live (402); sending pauses for an hour. |
| A device is missing in myEnergy | It needs a power sensor (device class *power*) and must be ticked in the setup. |
| Daily kWh stays at 0 | The device has no energy sensor in Home Assistant; power is still shown live. |

## Support

- Help: [myEnergy help – Live](https://myenergy-63712.web.app/hilfe#live)
- Email: support@gellclan.at (setup assistance by arrangement)
- Bugs: [GitHub issues](https://github.com/Gellclan/myenergy-homeassistant/issues)

## License

All rights reserved, see [LICENSE](LICENSE). Use only together with a myEnergy account.

## Development

The source lives in the folder `ha-integration/` of the myEnergy repository; this repository is produced from it with
`git subtree split --prefix ha-integration`. Tests: `python3 -m unittest discover -s tests` (pure logic) and `pytest`
with `pytest-homeassistant-custom-component` (Python ≥ 3.12).
