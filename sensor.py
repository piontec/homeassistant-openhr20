from datetime import datetime
import logging
import aiosqlite

from datetime import timedelta
from typing import Any, Callable, Dict, Optional

import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import Entity
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
    _LOGGER.info("starting openhr20")
    db_path = config[CONF_FILE_PATH]
    _LOGGER.debug(f"Trying to connect to sqlite DB at '{db_path}'.")
    async with aiosqlite.connect(db_path):
        _LOGGER.debug("DB connection successful")
    sensors = [
        OpenHR20Sensor(t[CONF_ID], t[CONF_NAME], db_path) for t in config[CONF_THERMO]
    ]
    async_add_entities(sensors, update_before_add=True)


class OpenHR20Sensor(Entity):
    """Representation of a GitHub Repo sensor."""

    def __init__(self, id: str, name: str, db_path: str) -> None:
        super().__init__()
        self.attrs: Dict[str, Any] = {}
        self._attr_unique_id = id
        self._name = name
        self._state = None
        self._available = True
        self._db_path = db_path
        self._attr_icon = "mdi:thermometer"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def unit_of_measurement(self) -> str:
        return TEMP_CELSIUS

    async def async_update(self):
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT * FROM log WHERE addr=(?) order by time desc limit 1",
                (self._attr_unique_id,),
            ) as cursor:
                async for row in cursor:
                    time = datetime.utcfromtimestamp(row[2])
                    self.attrs["mode"] = row[3]
                    self.attrs["valve"] = int(row[4])
                    real_temp = float(row[5]) / 100
                    self.attrs["wanted_temp"] = float(row[6]) / 100
                    self.attrs["battery_v"] = float(row[7]) / 1000
                    self.attrs["error"] = bool(row[8])
                    self.attrs["window"] = bool(row[9])
                    self.attrs["force"] = bool(row[10])
                    self._state = real_temp
        # set available  = True if update more recent than 5 minutes
        # self._available = datetime.utcnow() - time <= timedelta(minutes=5)
