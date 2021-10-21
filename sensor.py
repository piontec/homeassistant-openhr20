from datetime import datetime, timedelta
import logging
import aiosqlite
import os.path
import os

from typing import Any, Callable, Dict, Optional
from homeassistant.helpers.entity import Entity

from voluptuous.error import Error
from homeassistant import config_entries, core
from homeassistant.components.climate.const import (
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_OFF,
    HVAC_MODE_HEAT,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components.climate import ClimateEntity

from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
)

from homeassistant.const import (
    CONF_FILE_PATH,
    CONF_ID,
    CONF_NAME,
    TEMP_CELSIUS,
)

from .const import DOMAIN, CONF_THERMO


_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=1)

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


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    # DOMAIN key exc
    # config = hass.data[DOMAIN][config_entry.entry_id]
    thermo_id, thermo_name = config_entry.data[CONF_THERMO].split("=")
    db_path = config_entry.data[CONF_FILE_PATH]
    sensors = [
        OpenHR20Sensor(thermo_id, thermo_name, db_path, m[0], m[1])
        for m in ohr20_values_mapping
    ]
    async_add_entities(sensors, update_before_add=True)


class OpenHR20Sensor(Entity):
    def __init__(
        self,
        thermo_id: str,
        thermo_name: str,
        db_path: str,
        sensor_name: str,
        sensor_row: int,
    ) -> None:
        super().__init__()
        self.entity_description = f"OpenHR20 ID {thermo_id} - {sensor_name}"
        self._attr_unique_id = f"{thermo_id}-{sensor_name}"
        self._attr_name = sensor_name
        self._attr_state = None
        self._attr_available = True
        self._db_path = db_path
        self._thermo_id = thermo_id
        self._thermo_name = thermo_name
        self._sensor_row = sensor_row
        # self._attr_icon = "mdi:thermometer"

    async def async_update(self):
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT * FROM log WHERE addr=(?) order by time desc limit 1",
                (self._thermo_id,),
            ) as cursor:
                async for row in cursor:
                    self._attr_state = row[self._sensor_row]
                    # time = datetime.utcfromtimestamp(row[2])
        # set available  = True if update more recent than 5 minutes
        # self._available = datetime.utcnow() - time <= timedelta(minutes=5)

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._thermo_id)
            },
            "name": self._thermo_name,
            "manufacturer": "OpenHR20",
            "model": "HR20",
            "sw_version": "0.1.1",
        }


# async def async_setup_platform(
#     hass: HomeAssistantError,
#     config: ConfigType,
#     async_add_entities: Callable,
#     discovery_info: Optional[DiscoveryInfoType] = None,
# ) -> None:
#     _LOGGER.info("Starting openhr20")
#     db_path = config[CONF_FILE_PATH]
#     if not os.path.isfile(db_path):
#         raise Error(f"DB file '{db_path}' not found")
#     if not os.access(db_path, os.R_OK):
#         raise Error(f"DB file '{db_path}' is not readable")
#     if not os.access(db_path, os.W_OK):
#         raise Error(f"DB file '{db_path}' is not writable")
#     _LOGGER.debug(f"Trying to connect to sqlite DB at '{db_path}'.")
#     async with aiosqlite.connect(db_path):
#         _LOGGER.debug("DB connection successful")
#     sensors = [
#         OpenHR20Sensor(t[CONF_ID], t[CONF_NAME], db_path) for t in config[CONF_THERMO]
#     ]
#     # async_add_entities(sensors, update_before_add=True)
