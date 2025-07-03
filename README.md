# Babyschwimmen Nächster Termin - Home Assistant Sensor

This custom component for Home Assistant provides a sensor that displays the next appointment for the "Babyschwimmen" courses offered by [Kinder Spiel Sport](https://www.kinder-spiel-sport.de).

## Features

-   **Next Appointment Sensor**: Shows the date and time of the next swimming course as a timestamp.
-   **Attributes**: Provides detailed information as attributes:
    -   A human-readable description of the next appointment.
    -   Start and end times.
    -   Days until the next course.
    -   A list of the next 10 upcoming appointments.
-   **Automatic Updates**: The sensor polls the data from the official PDF document every 6 hours.

## Installation

1.  **HACS (Recommended)**
    -   Go to HACS > Integrations > Custom Repositories.
    -   Add the URL of this repository (`https://github.com/alexander-stolz/babyschwimmen-kinder-spiel-sport`) as a new repository with the category "Integration".
    -   Find the "Babyschwimmen Nächster Termin" integration and install it.

2.  **Manual Installation**
    -   Copy the `custom_components/babyschwimmen` directory to the `custom_components` directory in your Home Assistant configuration folder.

## Configuration

After installation, the integration can be configured via the Home Assistant user interface.

1.  Go to **Settings** > **Devices & Services**.
2.  Click the **+ Add Integration** button.
3.  Search for **"Babyschwimmen Nächster Termin"** and select it.
4.  Follow the on-screen instructions to complete the setup.

The sensor will be added automatically.

## Sensor

The integration creates one sensor:

-   `sensor.babyschwimmen_nachster_termin`

    The state of the sensor is a timestamp (e.g., `2025-10-25T10:00:00+00:00`). You can use this in templates and automations.

    The most important attributes are:
    -   `description`: A human-readable string, e.g., "25.10.2024 von 10:00 - 10:45 Uhr".
    -   `all_upcoming_dates`: A list of the next 10 appointments.

## Example Lovelace Card

```yaml
- type: entities
  entities:
    - entity: sensor.babyschwimmen_nachster_termin
      name: Nächster Schwimmtermin
      format: relative
    - entity: sensor.babyschwimmen_nachster_termin
      name: Wann
      attribute: description
```