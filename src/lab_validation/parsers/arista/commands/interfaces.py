import json
from collections.abc import Sequence
from typing import Any

from ..models.interfaces import AristaInterface

INTERFACES = "interfaces"
MTU = "mtu"
NAME = "name"
BANDWIDTH = "bandwidth"
LINE_PROTOCOL_STATUS = "lineProtocolStatus"


def parse_show_interfaces_json(text: str) -> Sequence[AristaInterface]:
    json_obj = json.loads(text)
    interfaces: list[AristaInterface] = []
    assert INTERFACES in json_obj, f"{json_obj} does not have key {INTERFACES}"
    for iface_name in json_obj[INTERFACES]:
        interfaces.append(parse_interface(json_obj[INTERFACES][iface_name]))
    return interfaces


def parse_interface(json_obj: dict[Any, Any]) -> AristaInterface:
    for key in [MTU, NAME, BANDWIDTH, LINE_PROTOCOL_STATUS]:
        assert key in json_obj, f"{json_obj} does not have key {key}"

    return AristaInterface(
        name=json_obj[NAME],
        mtu=json_obj[MTU],
        bandwidth=json_obj[BANDWIDTH],
        line=json_obj[LINE_PROTOCOL_STATUS] == "up",
    )
