from datetime import timedelta, datetime
import logging
import aiosqlite

from typing import Callable, Optional
from homeassistant.helpers.entity import Entity
from dataclasses import dataclass

from homeassistant import config_entries, core

from homeassistant.helpers.typing import (
    StateType,
)

from homeassistant.const import (
    CONF_FILE_PATH,
    ELECTRIC_POTENTIAL_VOLT,
    PERCENTAGE,
    TEMP_CELSIUS,
)

from .const import DBS_KEY, DOMAIN, CONF_THERMO


_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=4)

ohr20_values_mapping = [
    ("mode", 3),
    ("valve", 4),
    ("current_temperature", 5),
    ("target_temperature", 6),
    ("battery_v", 7),
    ("error", 8),
    ("window", 9),
    ("force", 10),
]


@dataclass
class OpenHR20EntityInfo:
    name: str
    db_selector: Callable[[aiosqlite.Row], StateType]
    icon_setter: Callable[[StateType], str]
    unit: Optional[str]


ohr20_entities_info = [
    OpenHR20EntityInfo("mode", lambda r: r[3], lambda _: "mdi:book-open", None),
    OpenHR20EntityInfo(
        "valve open", lambda r: int(r[4]), lambda _: "mdi:percent", PERCENTAGE
    ),
    OpenHR20EntityInfo(
        "current temperature",
        lambda r: float(r[5]) / 100,
        lambda _: "mdi:thermometer",
        TEMP_CELSIUS,
    ),
    OpenHR20EntityInfo(
        "target temperature",
        lambda r: float(r[6]) / 100,
        lambda _: "mdi:thermometer",
        TEMP_CELSIUS,
    ),
    OpenHR20EntityInfo(
        "battery voltage",
        lambda r: float(r[7]) / 1000,
        lambda v: "mdi:battery"
        if v and v > 2.4
        else "mdi:battery-50"
        if v and v > 2.2
        else "mdi:battery-10",
        ELECTRIC_POTENTIAL_VOLT,
    ),
    OpenHR20EntityInfo(
        "error",
        lambda r: bool(r[8]),
        lambda v: "mdi:alert-circle" if v else "mdi:alert-circle-outline",
        None,
    ),
    OpenHR20EntityInfo(
        "window",
        lambda r: bool(r[9]),
        lambda v: "mdi:window-open-variant" if v else "mdi:window-closed-variant",
        None,
    ),
    OpenHR20EntityInfo(
        "force",
        lambda r: bool(r[10]),
        lambda v: "mdi:flash" if v else "mdi:flash-off",
        None,
    ),
]


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    thermo_id, thermo_name = config_entry.data[CONF_THERMO].split("=")
    db_file = config_entry.data[CONF_FILE_PATH]
    _LOGGER.debug(f"Platform setup, db_file is '{db_file}'")
    sensors = [
        OpenHR20Sensor(thermo_id, thermo_name, db_file, ei)
        for ei in ohr20_entities_info
    ]
    async_add_entities(sensors, update_before_add=True)


class OpenHR20Sensor(Entity):
    def __init__(
        self,
        thermo_id: str,
        thermo_name: str,
        db_file: str,
        entity_info: OpenHR20EntityInfo,
    ) -> None:
        super().__init__()
        self._attr_unique_id = f"{thermo_id}-{entity_info.name}"
        self._attr_name = entity_info.name
        self._attr_state = None
        self._attr_available = True
        self._db_file = db_file
        self._thermo_id = thermo_id
        self._thermo_name = thermo_name
        self._icon_setter = entity_info.icon_setter
        self._attr_icon = entity_info.icon_setter(None)
        self._attr_unit_of_measurement = entity_info.unit
        self._db_selector = entity_info.db_selector

    async def async_update(self):
        _LOGGER.debug(f"Attempting DB update for openhr id '{self._thermo_id}'")
        async with aiosqlite.connect(self._db_file) as db:
            async with db.execute(
                "SELECT * FROM log WHERE addr=(?) order by time desc limit 1",
                (self._thermo_id,),
            ) as cursor:
                _LOGGER.debug(f"Got DB update for openhr id '{self._thermo_id}'")
                async for row in cursor:
                    self._attr_state = self._db_selector(row)
                    self._attr_icon = self._icon_setter(self._attr_state)
                    time = datetime.utcfromtimestamp(row[2])
                    # set available  = True if update more recent than 3 * SCAN_INTERVAL
                    self._attr_available = datetime.utcnow() - time <= SCAN_INTERVAL * 3

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._thermo_id)
            },
            "name": self._thermo_name,
            "manufacturer": "OpenHR20",
            "model": "Honeywell Rondostat HR20",
            "sw_version": "0.1.1",
        }
