"""Sensor for Babyschwimmen."""

import logging
import aiohttp
import re
import pypdf
import io
from datetime import datetime, timedelta, time
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.util import dt as dt_util
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=6)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Babyschwimmen sensor from a config entry."""
    session = async_get_clientsession(hass)
    sensor = BabyschwimmenSensor(session)
    async_add_entities([sensor], update_before_add=True)


async def get_pdf_link(session: aiohttp.ClientSession) -> str | None:
    """Get the link to the PDF file from the website."""
    base_url = "https://www.kinder-spiel-sport.de"
    try:
        async with session.get(base_url) as response:
            response.raise_for_status()
            page_content = await response.text()
        pdf_link_pattern = rf'href="({base_url}/_files/ugd/.+\.pdf)"'
        pdf_links = re.findall(pdf_link_pattern, page_content)
        return pdf_links[0] if pdf_links else None
    except aiohttp.ClientError as e:
        _LOGGER.error(f"Error fetching website content: {e}")
        return None


async def download_and_parse_pdf(session: aiohttp.ClientSession) -> str | None:
    """Download and parse the PDF file."""
    url = await get_pdf_link(session)
    if not url:
        _LOGGER.error("No PDF link found.")
        return None
    try:
        async with session.get(url, timeout=30) as response:
            response.raise_for_status()
            pdf_content = await response.read()
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except (aiohttp.ClientError, TimeoutError) as e:
        _LOGGER.error(f"Error downloading or parsing PDF: {e}")
        return None
    except Exception as e:
        _LOGGER.error(f"An unexpected error occurred while processing PDF: {e}")
        return None


def parse_swimming_dates(text: str) -> list[dict]:
    """Parse swimming dates from the PDF text."""
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
                start_time_obj = time(start_hour, start_min)
                end_time_obj = time(end_hour, end_min)
                dates.append(
                    {
                        "date": date_obj,
                        "start_time": start_time_obj,
                        "end_time": end_time_obj,
                        "additional_info": additional_info,
                    }
                )
            except ValueError:
                _LOGGER.warning(f"Could not parse date: {date_str}")
                continue
    return dates


def get_next_swimming_date(dates: list[dict]) -> dict | None:
    """Get the next upcoming swimming date."""
    if not dates:
        return None
    now = datetime.now()
    future_dates = [
        d for d in dates if datetime.combine(d["date"], d["start_time"]) >= now
    ]
    if not future_dates:
        return None
    future_dates.sort(key=lambda x: datetime.combine(x["date"], x["start_time"]))
    return future_dates[0]


class BabyschwimmenSensor(SensorEntity):
    """Representation of a Babyschwimmen Sensor."""

    _attr_name = "Babyschwimmen Nächster Termin"
    _attr_icon = "mdi:swim"
    _attr_unique_id = f"{DOMAIN}_next_date"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, session: aiohttp.ClientSession):
        """Initialize the sensor."""
        self._session = session
        self._attr_native_value = None
        self._attr_extra_state_attributes = {"status": "initializing"}

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        pdf_text = await download_and_parse_pdf(self._session)
        if not pdf_text:
            self._attr_extra_state_attributes["status"] = "error_pdf_download"
            return

        dates = parse_swimming_dates(pdf_text)
        if not dates:
            self._attr_extra_state_attributes["status"] = "no_dates_found"
            return

        next_date_info = get_next_swimming_date(dates)
        if not next_date_info:
            self._attr_extra_state_attributes["status"] = "no_future_dates"
            self._attr_native_value = None
            return

        next_datetime = datetime.combine(
            next_date_info["date"], next_date_info["start_time"]
        )
        # Convert to timezone-aware datetime using Home Assistant's default timezone
        self._attr_native_value = dt_util.as_local(next_datetime)

        today = datetime.now().date()
        future_dates = [
            d
            for d in dates
            if datetime.combine(d["date"], d["start_time"]) >= datetime.now()
        ][:10]

        all_upcoming = [
            {
                "date": d["date"].strftime("%d.%m.%Y"),
                "time": f'{d["start_time"].strftime("%H:%M")} - {d["end_time"].strftime("%H:%M")}',
                "info": d["additional_info"],
            }
            for d in future_dates
        ]

        self._attr_extra_state_attributes = {
            "description": (
                f'{next_date_info["date"].strftime("%d.%m.%Y")} von '
                f'{next_date_info["start_time"].strftime("%H:%M")} - '
                f'{next_date_info["end_time"].strftime("%H:%M")} Uhr'
            ),
            "next_start_time": next_date_info["start_time"].strftime("%H:%M"),
            "next_end_time": next_date_info["end_time"].strftime("%H:%M"),
            "next_date_info": next_date_info["additional_info"],
            "days_until": (next_date_info["date"] - today).days,
            "status": "ok",
            "all_upcoming_dates": all_upcoming,
        }

