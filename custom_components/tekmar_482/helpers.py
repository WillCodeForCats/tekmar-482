from __future__ import annotations

import ipaddress

from .const import DOMAIN_REGEX


def regBytes(integer):
    return divmod(integer, 0x100)


def degCtoF(degC):
    return (degC * 9 / 5) + 32


def degCtoE(degC):
    return 2 * degC


def degEtoC(degE):
    # degE = 2*(degC)
    return degE / 2


def degHtoF(degH):
    # degH = 10*(degF) + 850
    return (degH - 850) / 10


def degFtoC(degF):
    return (degF - 32) / 1.8


def degHtoC(degH):
    return degFtoC(degHtoF(degH))


def host_valid(host: str) -> bool:
    """Return True if hostname or IP address is valid."""
    try:
        return ipaddress.ip_address(host).version in (4, 6)
    except ValueError:
        return DOMAIN_REGEX.match(host)
