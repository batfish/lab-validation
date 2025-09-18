import json
from collections.abc import Sequence
from typing import Any

from ..models.routes import AristaEvpnRoute

ACTIVE = "active"
AS_PATH = "asPath"
AS_PATH_ENTRY = "asPathEntry"
AS_PATH_TYPE = "asPathType"
EVPN_ROUTES = "evpnRoutes"
EVPN_ROUTE_PATHS = "evpnRoutePaths"
IP_GEN_ADDR = "ipGenAddr"
IP_GEN_PREFIX = "ipGenPrefix"
ORIGIN = "origin"
LOCAL_PREFERENCE = "localPreference"
NEXT_HOP = "nextHop"
RD = "rd"
ROUTE_KEY_DETAIL = "routeKeyDetail"
ROUTE_TYPE = "routeType"
WEIGHT = "weight"
VRF = "vrf"


def parse_show_bgp_evpn_json(text: str) -> Sequence[AristaEvpnRoute]:
    json_obj = json.loads(text)
    routes: list[AristaEvpnRoute] = []
    if EVPN_ROUTES not in json_obj:
        return routes
    assert VRF in json_obj
    routes += _get_evpn_routes(json_obj[VRF], json_obj[EVPN_ROUTES])
    return routes


def _get_evpn_routes(vrf: str, json_obj: dict[Any, Any]) -> Sequence[AristaEvpnRoute]:
    routes: list[AristaEvpnRoute] = []
    for routes_obj in json_obj.values():
        assert ROUTE_KEY_DETAIL in routes_obj
        key_detail = routes_obj[ROUTE_KEY_DETAIL]
        assert IP_GEN_PREFIX in key_detail or IP_GEN_ADDR in key_detail
        assert RD in key_detail
        assert EVPN_ROUTE_PATHS in routes_obj

        network_prefix = (
            key_detail[IP_GEN_PREFIX]
            if IP_GEN_PREFIX in key_detail
            else key_detail[IP_GEN_ADDR]
        )
        rd = routes_obj[ROUTE_KEY_DETAIL][RD]

        for path in routes_obj[EVPN_ROUTE_PATHS]:
            assert AS_PATH_ENTRY in path
            assert AS_PATH in path[AS_PATH_ENTRY]
            assert AS_PATH_TYPE in path[AS_PATH_ENTRY]
            assert NEXT_HOP in path
            assert ROUTE_TYPE in path
            assert ACTIVE in path[ROUTE_TYPE]
            assert ORIGIN in path[ROUTE_TYPE]

            next_hop = path[NEXT_HOP] if path[NEXT_HOP] != "" else None
            routes.append(
                AristaEvpnRoute(
                    vrf=vrf,
                    network=network_prefix,
                    as_path=_get_as_path(path[AS_PATH_ENTRY][AS_PATH]),
                    as_path_type=path[AS_PATH_ENTRY][AS_PATH_TYPE],
                    local_preference=path.get(LOCAL_PREFERENCE, None),
                    weight=path.get(WEIGHT, None),
                    next_hop_ip=next_hop,
                    is_active=path[ROUTE_TYPE][ACTIVE],
                    origin=path[ROUTE_TYPE][ORIGIN],
                    route_distinguisher=rd,
                )
            )
    return routes


def _get_as_path(as_path: str) -> Sequence[int]:
    assert as_path[-1] == "i"
    return tuple(map(int, as_path.split()[:-1]))
