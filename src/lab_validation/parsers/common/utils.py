import ipaddress
import json
import re
from json import JSONDecoder
from typing import Any, Generator, Mapping, Optional


def normalized_network(network: str) -> str:
    return str(ipaddress.ip_network(network, strict=False))


def hex_to_ip(ip_in_hex: str) -> str:
    return str(ipaddress.ip_address(int(ip_in_hex, 16)))


def loads_multi_json(s: str) -> Generator[Mapping[str, Any], None, None]:
    _decoder: JSONDecoder = json.JSONDecoder()
    """A generator reading a sequence of JSON values from a string."""
    while s:
        s = s.strip()
        obj, pos = _decoder.raw_decode(s)
        if not pos:
            raise ValueError("no JSON object found at %i" % pos)
        yield obj
        s = s[pos:]


def convert_cisco_intf_name(intf: str) -> str:
    """return the full interface name

    Args:
        intf (`str`): Short version of the interface name

    Returns:
        Full interface name fit the standard

    Raises:
        None

    example:

        >>> convert_cisco_intf_name(intf='Eth2/1')
    """

    # Taken from Cisco genie project.
    # TODO: update and test
    convert = {
        "Eth": "Ethernet",
        "Lo": "Loopback",
        "Fa": "FastEthernet",
        "Fas": "FastEthernet",
        "Po": "Port-channel",
        "PO": "Port-channel",
        "Null": "Null",
        "Gi": "GigabitEthernet",
        "Gig": "GigabitEthernet",
        "GE": "GigabitEthernet",
        "Te": "TenGigabitEthernet",
        "mgmt": "mgmt",
        "Vl": "Vlan",
        "Tu": "Tunnel",
        "Fe": "",
        "Hs": "HSSI",
        "AT": "ATM",
        "Et": "Ethernet",
        "BD": "BDI",
        "Se": "Serial",
        "Fo": "FortyGigabitEthernet",
        "Hu": "HundredGigE",
        "vl": "vasileft",
        "vr": "vasiright",
        "BE": "Bundle-Ether",
    }
    m = re.search(r"([a-zA-Z]+)", intf)
    m1 = re.search(r"([\d/.]+)", intf)
    if m is None or m1 is None:
        return intf
    if hasattr(m, "group") and hasattr(m1, "group"):
        int_type = m.group(0)
        int_port = m1.group(0)
        if int_type in convert.keys():
            return convert[int_type] + int_port
        else:
            # Unifying interface names
            converted_intf = intf[0].capitalize() + intf[1:].replace(" ", "").replace(
                "ethernet", "Ethernet"
            )
            return converted_intf
    else:
        return intf


def optional_int_converter(x: Optional[Any]) -> Optional[int]:
    if x is None:
        return None
    return int(x)
