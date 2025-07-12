import json
import logging
import re
from typing import Dict, List, Optional, Sequence, Text, Tuple

from ..models.interfaces import JunosInterface, JunosInterfaceState
from .utils import remove_unused_lines

_bandwidth_map = {"k": 1000, "m": 1000000, "g": 1000000000}


def parse_show_interfaces_json(text: Text) -> Sequence[JunosInterface]:
    json_obj = json.loads(remove_unused_lines(text))
    interfaces: List[JunosInterface] = []
    for iface_data in json_obj["interface-information"][0]["physical-interface"]:
        admin_physical = _get_admin(iface_data["admin-status"][0]["data"])
        line_physical = _get_line(iface_data["oper-status"][0]["data"])
        junos_interface = JunosInterface(
            name=iface_data["name"][0]["data"],
            state=JunosInterfaceState(admin=admin_physical, line=line_physical),
            speed=_to_bandwidth(iface_data.get("speed", [{}])[0].get("data", None)),
            bandwidth=_to_bandwidth(
                iface_data.get("bandwidth", [{}])[0].get("data", None)
            ),
            mtu=iface_data.get("mtu", [{}])[0].get("data", None),
            interface_type="Physical interface",
        )
        interfaces.append(junos_interface)
        for logical_iface_data in iface_data.get("logical-interface", []):
            assert "if-config-flags" in logical_iface_data
            admin_logical, line_logical = _get_admin_logical(
                logical_iface_data.get("if-config-flags")[0],
                admin_physical,
                line_physical,
            )
            junos_interface = JunosInterface(
                name=logical_iface_data["name"][0]["data"],
                state=JunosInterfaceState(admin=admin_logical, line=line_logical),
                speed=_to_bandwidth(iface_data.get("speed", [{}])[0].get("data", None)),
                bandwidth=_to_bandwidth(
                    logical_iface_data.get("logical-interface-bandwidth", [{}])[0].get(
                        "data", None
                    )
                ),
                mtu=logical_iface_data.get("address-family", [{}])[0]
                .get("mtu", [{}])[0]
                .get("data", None),
                interface_type="Logical interface",
            )
            interfaces.append(junos_interface)
    return interfaces


def _get_admin(admin_status: Text) -> bool:
    if admin_status == "up":
        return True
    assert admin_status == "down"
    return False


def _get_line(line_status: Text) -> bool:
    if line_status == "up":
        return True
    assert line_status == "down"
    return False


def _get_admin_logical(
    admin_status: Dict, admin: bool, line: bool
) -> Tuple[bool, bool]:
    if "iff-up" in admin_status:
        return True, True
    elif "iff-down" in admin_status:
        return False, False
    else:
        return admin, line


def _to_bandwidth(bw: Optional[str]) -> Optional[int]:
    if bw is None:
        return None
    bw = bw.lower()
    logger = logging.getLogger(__name__)
    match = re.fullmatch(r"([0-9]+)([gmk])bps", bw)
    if match is None:
        logger.warning("Did not recognize bandwidth:{}".format(bw))
        return None
    return int(match[1]) * _bandwidth_map[match[2]]
