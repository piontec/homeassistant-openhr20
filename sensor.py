from datetime import datetime, timedelta
import logging
import aiosqlite
import os.path
import os

from typing import Any, Callable, Dict, Optional

import voluptuous as vol
from voluptuous.error import Error
from homeassistant.components.climate.const import (
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_OFF,
    HVAC_MODE_HEAT,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components.climate import ClimateEntity
import homeassistant.helpers.config_validation as cv

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

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=1)

CONF_THERMO = "thermostats"
THERMO_SCHEMA = vol.Schema(
    {vol.Required(CONF_ID): cv.positive_int, vol.Required(CONF_NAME): cv.string}
)

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA_BASE.extend(
    {
        vol.Required(CONF_FILE_PATH): cv.string,
        vol.Required(CONF_THERMO): vol.All(cv.ensure_list, [THERMO_SCHEMA]),
    }
)


async def async_setup_platform(
    hass: HomeAssistantError,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    _LOGGER.info("Starting openhr20")
    db_path = config[CONF_FILE_PATH]
    if not os.path.isfile(db_path):
        raise Error(f"DB file '{db_path}' not found")
    if not os.access(db_path, os.R_OK):
        raise Error(f"DB file '{db_path}' is not readable")
    if not os.access(db_path, os.W_OK):
        raise Error(f"DB file '{db_path}' is not writable")
    _LOGGER.debug(f"Trying to connect to sqlite DB at '{db_path}'.")
    async with aiosqlite.connect(db_path):
        _LOGGER.debug("DB connection successful")
    sensors = [
        OpenHR20Sensor(t[CONF_ID], t[CONF_NAME], db_path) for t in config[CONF_THERMO]
    ]
    async_add_entities(sensors, update_before_add=True)


class OpenHR20Sensor(ClimateEntity):
    def __init__(self, unique_id: str, name: str, db_path: str) -> None:
        super().__init__()
        self.attrs: Dict[str, Any] = {}
        self._attr_unique_id = unique_id
        self._name = name
        self._state = None
        self._available = True
        self._db_path = db_path
        self._attr_icon = "mdi:thermometer"
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_precision = 0.01
        self._attr_hvac_modes = [HVAC_MODE_HEAT]
        self._attr_hvac_mode = HVAC_MODE_HEAT
        self._attr_supported_features = SUPPORT_TARGET_TEMPERATURE

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                ("openhr20", self.unique_id)
            },
            "name": self.name,
            "manufacturer": "OpenHR20",
            "model": "Custom model 1",
            "sw_version": "0.1.1",
        }

    async def async_update(self):
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT * FROM log WHERE addr=(?) order by time desc limit 1",
                (self._attr_unique_id,),
            ) as cursor:
                async for row in cursor:
                    # time = datetime.utcfromtimestamp(row[2])
                    self._attr_extra_state_attributes = {}
                    self._attr_extra_state_attributes["mode"] = row[3]
                    self._attr_extra_state_attributes["valve"] = int(row[4])
                    self._attr_current_temperature = float(row[5]) / 100
                    self._attr_target_temperature = float(row[6]) / 100
                    self._attr_extra_state_attributes["battery_v"] = (
                        float(row[7]) / 1000
                    )
                    self._attr_extra_state_attributes["error"] = bool(row[8])
                    self._attr_extra_state_attributes["window"] = bool(row[9])
                    self._attr_extra_state_attributes["force"] = bool(row[10])
                    self._attr_hvac_action = (
                        CURRENT_HVAC_OFF
                        if self._attr_extra_state_attributes["valve"] == 0
                        else CURRENT_HVAC_HEAT
                    )
        # set available  = True if update more recent than 5 minutes
        # self._available = datetime.utcnow() - time <= timedelta(minutes=5)
