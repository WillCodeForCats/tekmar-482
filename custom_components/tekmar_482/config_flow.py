"""Config flow for the Tekmar Gateway 482 integration."""

from __future__ import annotations

from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_SETBACK_ENABLE,
    DEFAULT_HOST,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SETBACK_ENABLE,
    DOMAIN,
)
from .helpers import host_valid


@callback
def tekmar_482_entries(hass: HomeAssistant):
    """Return the hosts already configured."""
    return set(
        entry.data[CONF_HOST].lower()
        for entry in hass.config_entries.async_entries(DOMAIN)
    )


def generate_config_schema(step_id: str, user_input: dict[str, Any]) -> vol.Schema:
    """Generate config flow or repair schema."""
    schema: dict[vol.Marker, Any] = {}

    if step_id == "user":
        schema |= {vol.Required(CONF_NAME, default=user_input[CONF_NAME]): cv.string}

    if step_id in ["reconfigure", "user"]:
        schema |= {
            vol.Required(CONF_HOST, default=user_input[CONF_HOST]): cv.string,
            vol.Required(CONF_PORT, default=user_input[CONF_PORT]): vol.Coerce(int),
        }

    return vol.Schema(schema)


class TekmarGatewayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Tekmar Gateway configflow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> TekmarGatewayOptionsFlowHandler:
        """Create the options flow for Tekmar Gateway 482."""
        return TekmarGatewayOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial config flow step."""
        errors = {}

        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].lower()

            if not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"
            elif user_input[CONF_HOST] in tekmar_482_entries(self.hass):
                errors[CONF_HOST] = "already_configured"
            elif user_input[CONF_PORT] < 1:
                errors[CONF_PORT] = "invalid_tcp_port"
            elif user_input[CONF_PORT] > 65535:
                errors[CONF_PORT] = "invalid_tcp_port"
            else:
                await self.async_set_unique_id(user_input[CONF_NAME])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
        else:
            user_input = {
                CONF_NAME: DEFAULT_NAME,
                CONF_HOST: DEFAULT_HOST,
                CONF_PORT: DEFAULT_PORT,
            }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=user_input[CONF_NAME]): cv.string,
                    vol.Required(CONF_HOST, default=user_input[CONF_HOST]): cv.string,
                    vol.Required(CONF_PORT, default=user_input[CONF_PORT]): vol.Coerce(
                        int
                    ),
                },
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the reconfigure flow step."""
        errors = {}
        config_entry = self._get_reconfigure_entry()

        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].lower()

            other_hosts = tekmar_482_entries(self.hass) - {
                config_entry.data[CONF_HOST].lower()
            }

            if not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"
            elif user_input[CONF_HOST] in other_hosts:
                errors[CONF_HOST] = "already_configured"
            elif not 1 <= user_input[CONF_PORT] <= 65535:
                errors[CONF_PORT] = "invalid_tcp_port"
            else:
                # The entry's update listener reloads the integration.
                self.hass.config_entries.async_update_entry(
                    config_entry, data={**config_entry.data, **user_input}
                )
                return self.async_abort(reason="reconfigure_successful")
        else:
            user_input = {
                CONF_HOST: config_entry.data[CONF_HOST],
                CONF_PORT: config_entry.data.get(CONF_PORT, DEFAULT_PORT),
            }

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=generate_config_schema("reconfigure", user_input),
            errors=errors,
        )


class TekmarGatewayOptionsFlowHandler(OptionsFlow):
    """Handle an options flow for Tekmar Gateway 482."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial options flow step."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        else:
            if self.config_entry.options.get(CONF_SETBACK_ENABLE) is None:
                user_input = {
                    CONF_SETBACK_ENABLE: DEFAULT_SETBACK_ENABLE,
                }

            else:
                user_input = {
                    CONF_SETBACK_ENABLE: self.config_entry.options.get(
                        CONF_SETBACK_ENABLE
                    ),
                }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SETBACK_ENABLE, default=user_input[CONF_SETBACK_ENABLE]
                    ): cv.boolean,
                },
            ),
            errors=errors,
        )
