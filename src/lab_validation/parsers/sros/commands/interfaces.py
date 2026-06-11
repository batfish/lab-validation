import json
from collections.abc import Sequence

from ..models.interfaces import SrosInterface

# Top-level key in `info json /state router "Base" interface` output.
_INTERFACE = "nokia-state:interface"


def parse_interface_state_json(text: str) -> Sequence[SrosInterface]:
    """Parse ``info json /state router "Base" interface`` into SrosInterfaces.

    An empty object (``{}``) is the valid response for an instance with no
    interfaces (e.g. a VPRN whose interface state path returns nothing) and
    yields no interfaces.
    """
    obj = json.loads(text)
    if not obj:
        return []
    assert _INTERFACE in obj, f"missing '{_INTERFACE}' in interface state"
    interfaces: list[SrosInterface] = []
    for entry in obj[_INTERFACE]:
        ipv4 = entry.get("ipv4", {})
        primary = ipv4.get("primary", {})
        interfaces.append(
            SrosInterface(
                name=entry["interface-name"],
                oper_up=entry["oper-state"] == "up",
                ipv4_up=ipv4.get("oper-state") == "up",
                primary_address=primary.get("oper-address"),
                if_index=entry.get("if-index"),
                mtu=entry.get("oper-ip-mtu"),
            )
        )
    return interfaces
