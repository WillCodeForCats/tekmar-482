import voluptuous as vol
import ipaddress
import re

from homeassistant import config_entries
from homeassistant.const import (
    CONF_NAME, CONF_HOST, CONF_PORT
)
import homeassistant.helpers.config_validation as cv
from .const import (
    DOMAIN, DEFAULT_NAME, DEFAULT_HOST, DEFAULT_PORT,
    DEFAULT_SETBACK_ENABLE, CONF_SETBACK_ENABLE
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.config_entries import ConfigEntry


def host_valid(host):
    """Return True if hostname or IP address is valid."""
    try:
        if ipaddress.ip_address(host).version == 4:
            return True
    except ValueError:
        disallowed = re.compile(r"[^a-zA-Z\d\-]")
        return all(x and not disallowed.search(x) for x in host.split("."))

@callback
def tekmar_482_entries(hass: HomeAssistant):
    """Return the hosts already configured."""
    return set(
        entry.data[CONF_HOST] for entry in hass.config_entries.async_entries(DOMAIN)
    )

class TekmarGatewayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Tekmar Gateway configflow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        return TekmarGatewayOptionsFlowHandler(config_entry)

    def _host_in_configuration_exists(self, host) -> bool:
        """Return True if host exists in configuration."""
        if host in tekmar_482_entries(self.hass):
            return True
        return False

    async def async_step_user(self, user_input = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            
            if self._host_in_configuration_exists(user_input[CONF_HOST]):
                errors[CONF_HOST] = "already_configured"
            elif not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"
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
            step_id = "user",
            data_schema = vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=user_input[CONF_NAME]
                    ): cv.string,
                    vol.Required(
                        CONF_HOST, default=user_input[CONF_HOST]
                    ): cv.string,
                    vol.Required(
                        CONF_PORT, default=user_input[CONF_PORT]
                    ): vol.Coerce(int),
                },
            ),
            errors = errors
        )
    

class TekmarGatewayOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input = None) -> FlowResult:
        errors = {}

        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                title = "",
                data = user_input
            )
        else:
            if self.config_entry.options.get(CONF_SETBACK_ENABLE) is None:
                user_input = {
                    CONF_SETBACK_ENABLE: DEFAULT_SETBACK_ENABLE,
                }
            
            else:
                user_input = {
                    CONF_SETBACK_ENABLE: self.config_entry.options.get(CONF_SETBACK_ENABLE),
                }

        return self.async_show_form(
            step_id = "init",
            data_schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_SETBACK_ENABLE, default=user_input[CONF_SETBACK_ENABLE]
                    ): cv.boolean,
                },
            ),
            errors = errors
        )
