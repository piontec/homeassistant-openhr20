"""The openhr20 integration."""
from __future__ import annotations
import logging

import aiosqlite

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_FILE_PATH
from homeassistant.core import HomeAssistant

from .const import DBS_KEY, DOMAIN

PLATFORMS: list[str] = ["sensor"]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up openhr20 from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    db_file = entry.data[CONF_FILE_PATH]
    hass.data[DOMAIN].setdefault(DBS_KEY, {})
    if db_file not in hass.data[DOMAIN][DBS_KEY]:
        _LOGGER.info(f"DB connection for file '{db_file}' not found, creating it")
        hass.data[DOMAIN][DBS_KEY][db_file] = await aiosqlite.connect(db_file)

    _LOGGER.debug("calling setup_platforms")
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # if you saved any sessions, remove them here
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        db_file = entry.data[CONF_FILE_PATH]
        if db_file in hass.data[DOMAIN][DBS_KEY]:
            await hass.data[DOMAIN][DBS_KEY][db_file].close()
            hass.data[DOMAIN][DBS_KEY].pop(db_file)

    return unload_ok
