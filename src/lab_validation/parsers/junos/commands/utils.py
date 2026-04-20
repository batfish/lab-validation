import re


def remove_unused_lines(text: str) -> str:
    """
    remove "{master:0}" at the end to make the text a valid json string
    """
    match = re.fullmatch(r"(?P<json_text>.*){master:0}.*", text, re.DOTALL)

    if match is None:
        return text
    else:
        return match["json_text"]


# Known Junos RIB suffixes. These appear as the tail of a table name.
# Longest first so bgp.evpn.0 matches before evpn.0
_KNOWN_RIBS = (
    "bgp.evpn.0",
    "inetflow.0",
    "inet6.0",
    "inet.0",
    "evpn.0",
    "mpls.0",
)


def _parse_table_header(table_name: str) -> tuple[str, str]:
    """Parse a Junos routing table name into (vrf, rib).

    Examples:
        "inet.0" -> ("default", "inet.0")
        "TENANT-A.inet.0" -> ("TENANT-A", "inet.0")
        "bgp.evpn.0" -> ("default", "bgp.evpn.0")
        "TENANT-A.evpn.0" -> ("TENANT-A", "evpn.0")
        "mpls.0" -> ("default", "mpls.0")
    """
    for rib in _KNOWN_RIBS:
        if table_name == rib:
            return "default", rib
        if table_name.endswith("." + rib):
            vrf = table_name[: -(len(rib) + 1)]
            return vrf, rib
    return "default", table_name
