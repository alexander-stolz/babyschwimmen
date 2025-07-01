import logging
import aiohttp
import re
import PyPDF2
import io
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=6)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    sensor = BabyschwimmenSensor(hass)
    await sensor.async_update()
    async_add_entities([sensor])


async def async_setup_entry(hass, entry, async_add_entities):
    sensor = BabyschwimmenSensor(hass)
    await sensor.async_update()
    async_add_entities([sensor])


async def get_pdf_link(session):
    base_url = "https://www.kinder-spiel-sport.de"
    try:
        async with session.get(base_url) as response:
            page_content = await response.text()
        pdf_link_pattern = rf'href="({base_url}/_files/ugd/.+\.pdf)"'
        pdf_links = re.findall(pdf_link_pattern, page_content)
        return pdf_links[0] if pdf_links else None
    except Exception as e:
        _LOGGER.error(f"Fehler beim Laden der Webseite: {e}")
        return None


async def download_and_parse_pdf(session):
    url = await get_pdf_link(session)
    if not url:
        _LOGGER.error("Kein PDF-Link gefunden.")
        return None
    try:
        async with session.get(url, timeout=30) as response:
            pdf_content = await response.read()
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        _LOGGER.error(f"Fehler beim Herunterladen/Parsen der PDF: {e}")
        return None


def parse_swimming_dates(text):
    if not text:
        return []
    dates = []
    pattern = r"(\d{2}\.\d{2}\.\d{4})\s+(.*?)(?=\n|\d{2}\.\d{2}\.\d{4}|$)"
    matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
    for date_str, time_info in matches:
        time_info = time_info.strip()
        if "Kein Unterricht" in time_info:
            continue
        time_pattern = r"(\d{1,2})\.(\d{2})\s*[-–]\s*(\d{1,2})\.(\d{2})\s*Uhr\s*(.*)?"
        time_match = re.search(time_pattern, time_info)
        if time_match:
            start_hour = int(time_match.group(1))
            start_min = int(time_match.group(2))
            end_hour = int(time_match.group(3))
            end_min = int(time_match.group(4))
            additional_info = time_match.group(5)
            if additional_info:
                additional_info = additional_info.strip()
            else:
                additional_info = ""
            try:
                date_obj = datetime.strptime(date_str, "%d.%m.%Y").date()
                start_time = f"{start_hour:02d}:{start_min:02d}"
                end_time = f"{end_hour:02d}:{end_min:02d}"
                dates.append(
                    {
                        "date": date_obj,
                        "date_str": date_str,
                        "start_time": start_time,
                        "end_time": end_time,
                        "time_range": f"{start_time} - {end_time}",
                        "additional_info": additional_info,
                    }
                )
            except ValueError:
                continue
    return dates


def get_next_swimming_date(dates):
    if not dates:
        return None
    today = datetime.now().date()
    future_dates = [d for d in dates if d["date"] >= today]
    if not future_dates:
        return None
    future_dates.sort(key=lambda x: x["date"])
    return future_dates[0]


class BabyschwimmenSensor(SensorEntity):
    _attr_name = "Babyschwimmen Nächster Termin"
    _attr_icon = "mdi:swim"
    _attr_unique_id = "babyschwimmen_next_date"

    def __init__(self, hass):
        self.hass = hass
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    async def async_update(self):
        session = async_get_clientsession(self.hass)
        pdf_text = await download_and_parse_pdf(session)
        if not pdf_text:
            self._attr_native_value = "Fehler beim Laden der PDF"
            self._attr_extra_state_attributes = {"status": "error"}
            return
        dates = parse_swimming_dates(pdf_text)
        if not dates:
            self._attr_native_value = "Keine Termine gefunden"
            self._attr_extra_state_attributes = {"status": "no_dates"}
            return
        next_date = get_next_swimming_date(dates)
        if not next_date:
            self._attr_native_value = "Keine zukünftigen Termine"
            self._attr_extra_state_attributes = {"status": "no_future_dates"}
            return
        today = datetime.now().date()
        days_until = (next_date["date"] - today).days
        future_dates = [d for d in dates if d["date"] >= today][:10]
        all_upcoming = []
        for date in future_dates:
            all_upcoming.append(
                {
                    "date": date["date_str"],
                    "time": date["time_range"],
                    "info": date["additional_info"],
                }
            )
        self._attr_native_value = (
            f"{next_date['date_str']} "
            f"von {next_date['start_time']} - {next_date['end_time']} Uhr"
        )
        self._attr_extra_state_attributes = {
            "next_time": next_date["time_range"],
            "next_start_time": next_date["start_time"],
            "next_end_time": next_date["end_time"],
            "next_datetime": f"{next_date['date_str']} {next_date['start_time']}",
            "next_end_datetime": f"{next_date['date_str']} {next_date['end_time']}",
            "next_date_info": next_date["additional_info"],
            "days_until": days_until,
            "status": "ok",
            "all_upcoming_dates": all_upcoming,
        }
