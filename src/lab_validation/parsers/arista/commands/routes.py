import json
from collections.abc import Sequence
from typing import Any

from ..models.routes import AristaIpRoute

INTERFACE = "interface"
METRIC = "metric"
NEXTHOP_ADDR = "nexthopAddr"
PREFERENCE = "preference"
ROUTES = "routes"
ROUTE_TYPE = "routeType"
VIAS = "vias"
VNI = "vni"
VRFS = "vrfs"
VTEP_ADDR = "vtepAddr"


def parse_show_ip_route_vrf_all_json(text: str) -> Sequence[AristaIpRoute]:
    json_obj = json.loads(text)
    routes: list[AristaIpRoute] = []
    assert VRFS in json_obj
    for vrf_name in json_obj[VRFS]:
        if ROUTES in json_obj[VRFS][vrf_name]:
            routes += _get_routes(vrf_name, json_obj[VRFS][vrf_name][ROUTES])
    return routes


def _get_routes(vrf: str, json_obj: dict[Any, Any]) -> Sequence[AristaIpRoute]:
    routes: list[AristaIpRoute] = []
    for network in json_obj:
        routes_obj = json_obj[network]
        assert VIAS in routes_obj
        assert ROUTE_TYPE in routes_obj

        if not len(routes_obj[VIAS]):
            # Discard route. TODO Are routes with no vias always discard routes?
            routes.append(
                AristaIpRoute(
                    vrf=vrf,
                    network=network,
                    next_hop_int="Null0",
                    next_hop_ip=None,
                    protocol=routes_obj[ROUTE_TYPE],
                    preference=routes_obj.get(PREFERENCE, None),
                    metric=routes_obj.get(METRIC, None),
                    vni=None,
                    vtep_ip=None,
                )
            )
            continue

        for vias in routes_obj[VIAS]:
            routes.append(
                AristaIpRoute(
                    vrf=vrf,
                    network=network,
                    next_hop_int=vias.get(INTERFACE, None),
                    next_hop_ip=vias.get(NEXTHOP_ADDR, None),
                    protocol=routes_obj[ROUTE_TYPE],
                    preference=routes_obj.get(PREFERENCE, None),
                    metric=routes_obj.get(METRIC, None),
                    vni=vias.get(VNI, None),
                    vtep_ip=vias.get(VTEP_ADDR, None),
                )
            )
    return routes
