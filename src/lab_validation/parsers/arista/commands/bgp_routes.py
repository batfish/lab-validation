import json
from collections.abc import Sequence
from typing import Any

from ..models.routes import AristaBgpRoute

ACTIVE = "active"
ADDRESS = "address"
AS_PATH = "asPath"
AS_PATH_ENTRY = "asPathEntry"
AS_PATH_TYPE = "asPathType"
BGP_ROUTE_ENTRIES = "bgpRouteEntries"
BGP_ROUTE_PATHS = "bgpRoutePaths"
ECMP = "ecmp"
LOCAL_PREFERENCE = "localPreference"
MED = "med"
NEXT_HOP = "nextHop"
NOT_INSTALLED_REASON = "notInstalledReason"
ORIGIN = "origin"
ROUTE_TYPE = "routeType"
VRFS = "vrfs"
WEIGHT = "weight"


def parse_show_ip_bgp_vrf_all_json(text: str) -> Sequence[AristaBgpRoute]:
    json_obj = json.loads(text)
    routes: list[AristaBgpRoute] = []
    if VRFS not in json_obj:
        return routes
    for vrf_name in json_obj[VRFS]:
        if BGP_ROUTE_ENTRIES in json_obj[VRFS][vrf_name]:
            routes += _get_bgp_routes(
                vrf_name, json_obj[VRFS][vrf_name][BGP_ROUTE_ENTRIES]
            )
    return routes


def _get_bgp_routes(vrf: str, json_obj: dict[Any, Any]) -> Sequence[AristaBgpRoute]:
    routes: list[AristaBgpRoute] = []
    for network in json_obj:
        routes_obj = json_obj[network]
        assert BGP_ROUTE_PATHS in routes_obj
        assert ADDRESS in routes_obj

        for path in routes_obj[BGP_ROUTE_PATHS]:
            assert AS_PATH_ENTRY in path
            assert AS_PATH in path[AS_PATH_ENTRY]
            assert ROUTE_TYPE in path
            assert ACTIVE in path[ROUTE_TYPE]
            next_hop_ip = path.get(NEXT_HOP)
            if next_hop_ip == "":
                next_hop_ip = None

            as_path, origin_type = _get_as_path_and_origin(path[AS_PATH_ENTRY][AS_PATH])
            routes.append(
                AristaBgpRoute(
                    vrf=vrf,
                    network=network,
                    next_hop_ip=next_hop_ip,
                    local_preference=path.get(LOCAL_PREFERENCE, None),
                    metric=path.get(MED, None),
                    as_path=as_path,
                    weight=get_weight(path.get(WEIGHT), next_hop_ip),
                    is_active=path[ROUTE_TYPE][ACTIVE],
                    is_ecmp=path[ROUTE_TYPE][ECMP],
                    not_installed_reason=path[ROUTE_TYPE].get(
                        NOT_INSTALLED_REASON, None
                    ),
                    origin_protocol=get_origin_protocol(
                        path[AS_PATH_ENTRY].get(AS_PATH_TYPE)
                    ),
                    origin_type=origin_type,
                )
            )
    return routes


def get_weight(weight: int | None, next_hop_ip: str | None) -> int | None:
    if next_hop_ip is None and weight is None:
        # ribd(single-agent) EOS does not provide weight for local routes
        return 0
    else:
        return weight


_ORIGIN_TYPE_MAP = {"i": "igp", "e": "egp", "?": "incomplete"}

_ORIGIN_PROTOCOL_MAP = {
    "Internal": "ibgp",
    "External": "bgp",
    "Local": "bgp",
}


def _get_as_path_and_origin(as_path: str) -> tuple[Sequence[int], str]:
    parts = as_path.split()
    origin_char = parts[-1]
    origin_type = _ORIGIN_TYPE_MAP[origin_char]
    as_numbers = tuple(map(int, parts[:-1]))
    return as_numbers, origin_type


def get_origin_protocol(as_path_type: str | None) -> str | None:
    if as_path_type is None:
        return None
    return _ORIGIN_PROTOCOL_MAP.get(as_path_type)
