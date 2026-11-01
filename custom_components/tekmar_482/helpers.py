from __future__ import annotations

import ipaddress

from .const import DOMAIN_REGEX


def regBytes(integer):
    """Split a 16-bit register value into (high, low) bytes."""
    return divmod(integer, 0x100)


def degCtoF(degC):
    """Convert degrees Celsius to degrees Fahrenheit."""
    return (degC * 9 / 5) + 32


def degCtoE(degC):
    """Convert degrees Celsius to degE, where degE = 2 * degC."""
    return 2 * degC


def degEtoC(degE):
    """Convert degE to degrees Celsius, where degE = 2 * degC."""
    return degE / 2


def degHtoF(degH):
    """Convert degH to degrees Fahrenheit, where degH = 10 * degF + 850."""
    return (degH - 850) / 10


def degFtoC(degF):
    """Convert degrees Fahrenheit to degrees Celsius."""
    return (degF - 32) / 1.8


def degHtoC(degH):
    """Convert degH to degrees Celsius."""
    return degFtoC(degHtoF(degH))


def host_valid(host: str) -> bool:
    """Return True if hostname or IP address is valid."""
    try:
        return ipaddress.ip_address(host).version in (4, 6)
    except ValueError:
        return DOMAIN_REGEX.match(host)
