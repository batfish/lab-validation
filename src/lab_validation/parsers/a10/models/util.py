def canonicalize_interface_opt(iface: str | None) -> str | None:
    """Converts an interface name from show data into a canonical interface name."""
    if iface is None:
        return None
    return canonicalize_interface(iface)


def canonicalize_interface(iface: str) -> str:
    """Converts an interface name from show data into a canonical interface name."""
    if iface.startswith("ve"):
        return "VirtualEthernet" + iface[2:]
    return iface[0].capitalize() + iface[1:]
