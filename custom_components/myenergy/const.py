"""Konstanten der myEnergy-Integration."""
DOMAIN = "myenergy"
INGEST_URL = "https://europe-west1-myenergy-63712.cloudfunctions.net/ingest"
CONF_KEY = "key"
CONF_PLUGS = "plugs"
CONF_METER_POWER = "meter_power"
CONF_METER_IMPORT = "meter_import"
CONF_METER_EXPORT = "meter_export"
INTERVAL_S = 30
DAYS_EVERY_S = 300
# Home Assistant meldet nur Änderungen; so lange ohne Meldung gilt eine Steckdose als offline (wie STALE_S im Pi-Dienst)
STALE_S = 86400
# Ohne Plan Live (HTTP 402) nur noch stündlich nachfragen
NO_PLAN_RETRY_S = 3600
