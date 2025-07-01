# HA Sensor: Nächster Termin Babyschwimmen für kinder-spiel-sport.de

## Zusammenfassung

Home Assistant Custom Component: Sensor, der automatisch den nächsten Termin für das Babyschwimmen von der Website [kinder-spiel-sport.de](https://www.kinder-spiel-sport.de) ausliest.

Liefert, neben `sensor.babyschwimmen_nachster_termin`, folgende Attribute:

- `next_time`: Zeitspanne des nächsten Termins
- `next_start_time` / `next_end_time`: Start- und Endzeit
- `next_datetime` / `next_end_datetime`: Datum und Zeit als String
- `next_date_info`: Zusatzinfo (z.B. Kursname)
- `days_until`: Tage bis zum nächsten Termin
- `all_upcoming_dates`: Liste der nächsten 10 Termine

## Installation

1. Kopiere das Verzeichnis `babyschwimmen` in den `custom_components`-Ordner:

   ```
   <config>/custom_components/babyschwimmen/
   ```

2. Füge folgenden Eintrag zur `configuration.yaml` hinzu:

```yaml
sensor:
  - platform: babyschwimmen
```

3. Starte Home Assistant neu.


## Lizenz

MIT
