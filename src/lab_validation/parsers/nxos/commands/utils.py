import re


def to_interface_name(name: str) -> str:
    """Return the canonical interface name.

    Mostly geared at cisco devices.
    """

    # TODO: add more when we find other type of interfaces
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
        "BD": "BridgeDomain",
        "Se": "Serial",
        "Fo": "FortyGigabitEthernet",
        "Hu": "HundredGigE",
        "vl": "vasileft",
        "rl": "vasiright",
    }
    m = re.search(r"([a-zA-Z]+)", name)
    m1 = re.search(r"([\d/.]+)", name)
    if m is not None and m1 is not None:
        int_type = m.group(0)
        int_port = m1.group(0)
        if int_type in convert.keys():
            return convert[int_type] + int_port
        else:
            # Unifying interface names
            converted_intf = name[0].capitalize() + name[1:].replace(" ", "").replace(
                "ethernet", "Ethernet"
            )
            return converted_intf
    else:
        return name
