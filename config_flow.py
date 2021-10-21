"""Config flow for openhr20 integration."""
from __future__ import annotations

import logging
import os
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

import aiosqlite

from homeassistant.const import (
    CONF_FILE_PATH,
    CONF_ID,
    CONF_NAME,
)
from homeassistant.exceptions import HomeAssistantError

import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_THERMO

_LOGGER = logging.getLogger(__name__)

OHR20_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_FILE_PATH, default="/workspaces/core/openhr20.sqlite"): str,
        vol.Required(CONF_THERMO, default="10=sypialnia"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    ohr20_id, name = data[CONF_THERMO].split("=")

    db_path = data[CONF_FILE_PATH]
    if not os.path.isfile(db_path):
        raise HomeAssistantError(f"DB file '{db_path}' not found")
    if not os.access(db_path, os.R_OK):
        raise HomeAssistantError(f"DB file '{db_path}' is not readable")
    if not os.access(db_path, os.W_OK):
        raise HomeAssistantError(f"DB file '{db_path}' is not writable")
    _LOGGER.debug(f"Trying to connect to sqlite DB at '{db_path}'.")
    async with aiosqlite.connect(db_path):
        _LOGGER.debug("DB connection successful")
    # Return info that you want to store in the config entry.
    return {"title": name, "unique_id": ohr20_id}


class OpenHR20ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for openhr20."""

    VERSION = 1
    data: dict[str, Any] | None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Invoked when a user initiates a flow via the user interface."""
        errors: dict[str, str] = {}
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=OHR20_SCHEMA)

        try:
            info = await validate_input(self.hass, user_input)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=OHR20_SCHEMA, errors=errors
        )
