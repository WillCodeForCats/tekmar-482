"""Repairs for Tekmar 482 Gateway."""

from __future__ import annotations

from typing import cast

from homeassistant import data_entry_flow
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from .const import DEVICE_FEATURES
from .helpers import host_valid
from .hub import async_save_device_override

CONF_DEVICE_TYPE = "device_type"


class CheckConfigurationRepairFlow(RepairsFlow):
    """Handler for an issue fixing flow."""

    _entry: ConfigEntry

    def __init__(self, entry: ConfigEntry) -> None:
        """Create flow."""

        self._entry = entry
        super().__init__()

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of a fix flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the confirm step of a fix flow."""
        errors = {}

        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].lower()

            if not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"
            elif user_input[CONF_PORT] < 1 or user_input[CONF_PORT] > 65535:
                errors[CONF_PORT] = "invalid_tcp_port"
            else:
                self.hass.config_entries.async_update_entry(
                    self._entry, data={**self._entry.data, **user_input}
                )
                return self.async_create_entry(title="", data={})
        else:
            user_input = {
                CONF_HOST: self._entry.data[CONF_HOST],
                CONF_PORT: self._entry.data[CONF_PORT],
            }

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=user_input[CONF_HOST]): cv.string,
                    vol.Required(CONF_PORT, default=user_input[CONF_PORT]): vol.Coerce(
                        int
                    ),
                }
            ),
            errors=errors,
        )


def _device_type_options() -> list[SelectOptionDict]:
    """Return the known device types as select options, sorted by model."""
    return [
        SelectOptionDict(
            value=str(type_id),
            label=f"{features['model']} {features['type'].capitalize()} ({type_id})",
        )
        for type_id, features in sorted(
            DEVICE_FEATURES.items(), key=lambda item: (item[1]["model"], item[0])
        )
    ]


class UnknownDeviceRepairFlow(RepairsFlow):
    """Let the user identify a device the gateway reported with an unknown type."""

    def __init__(self, entry: ConfigEntry, address: int, reported_type: int) -> None:
        """Create flow."""
        self._entry = entry
        self._address = address
        self._reported_type = reported_type
        super().__init__()

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of a fix flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Ask which known device type this device is."""
        if user_input is not None:
            await async_save_device_override(
                self.hass,
                self._entry.entry_id,
                self._address,
                self._reported_type,
                int(user_input[CONF_DEVICE_TYPE]),
            )
            self.hass.config_entries.async_schedule_reload(self._entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_TYPE): SelectSelector(
                        SelectSelectorConfig(
                            options=_device_type_options(),
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            description_placeholders={
                "address": str(self._address),
                "reported_type": str(self._reported_type),
            },
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow."""

    if not data or "entry_id" not in data:
        return ConfirmRepairFlow()

    entry_id = cast(str, data["entry_id"])

    if (entry := hass.config_entries.async_get_entry(entry_id)) is not None:
        if issue_id == "check_configuration":
            return CheckConfigurationRepairFlow(entry)
        if issue_id.startswith("unknown_device_"):
            return UnknownDeviceRepairFlow(
                entry, cast(int, data["address"]), cast(int, data["reported_type"])
            )
    return ConfirmRepairFlow()
