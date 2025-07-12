from typing import Any, Dict, List, Sequence, Text

from ...common.utils import loads_multi_json
from ..models.routes import FrrIpRoute


def parse_show_ip_route_vrf_all_json(text: Text) -> Sequence[FrrIpRoute]:
    multi_json_obj = loads_multi_json(text)
    routes: List[FrrIpRoute] = []

    for json_obj in multi_json_obj:
        for route_key, route_json in json_obj.items():
            for route in route_json:
                routes += _get_route(route)
    return routes


def _get_route(route_json: Dict[Any, Any]) -> List[FrrIpRoute]:
    assert_list = ["prefix", "nexthops", "protocol"]
    assert all(item in route_json for item in assert_list)
    route: List[FrrIpRoute] = []
    for i in range(len(route_json["nexthops"])):
        route += [
            FrrIpRoute(
                # We only have `vrf-id` available, We will do mapping in validation.
                vrf=route_json.get("vrfId"),
                # Cumulus escapes prefixes in json output, so 10.0.0.0/8 -> 10.0.0.0\\/8
                network=route_json["prefix"].replace(r"\/", "/"),
                next_hop_int=route_json["nexthops"][i].get("interfaceName"),
                next_hop_ip=route_json["nexthops"][i].get("ip"),
                protocol=route_json["protocol"],
                admin_distance=route_json.get("distance", 0),
                metric=route_json.get("metric", 0),
                active=route_json.get("selected", False),
                blackhole=route_json["nexthops"][i].get("blackhole", False),
            )
        ]
    return route
