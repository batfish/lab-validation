import json
from typing import Any, Dict, List, Optional, Sequence

from ..models.routes import AristaBgpRoute

ACTIVE = "active"
ADDRESS = "address"
AS_PATH = "asPath"
AS_PATH_ENTRY = "asPathEntry"
BGP_ROUTE_ENTRIES = "bgpRouteEntries"
BGP_ROUTE_PATHS = "bgpRoutePaths"
ECMP = "ecmp"
LOCAL_PREFERENCE = "localPreference"
MED = "med"
NEXT_HOP = "nextHop"
NOT_INSTALLED_REASON = "notInstalledReason"
ROUTE_TYPE = "routeType"
VRFS = "vrfs"
WEIGHT = "weight"


def parse_show_ip_bgp_vrf_all_json(text: str) -> Sequence[AristaBgpRoute]:
    json_obj = json.loads(text)
    routes: List[AristaBgpRoute] = []
    assert VRFS in json_obj
    for vrf_name in json_obj[VRFS]:
        if BGP_ROUTE_ENTRIES in json_obj[VRFS][vrf_name]:
            routes += _get_bgp_routes(
                vrf_name, json_obj[VRFS][vrf_name][BGP_ROUTE_ENTRIES]
            )
    return routes


def _get_bgp_routes(vrf: str, json_obj: Dict[Any, Any]) -> Sequence[AristaBgpRoute]:
    routes: List[AristaBgpRoute] = []
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

            routes.append(
                AristaBgpRoute(
                    vrf=vrf,
                    network=network,
                    next_hop_ip=next_hop_ip,
                    local_preference=path.get(LOCAL_PREFERENCE, None),
                    metric=path.get(MED, None),
                    as_path=_get_as_path(path[AS_PATH_ENTRY][AS_PATH]),
                    weight=get_weight(path.get(WEIGHT), next_hop_ip),
                    is_active=path[ROUTE_TYPE][ACTIVE],
                    is_ecmp=path[ROUTE_TYPE][ECMP],
                    not_installed_reason=path[ROUTE_TYPE].get(
                        NOT_INSTALLED_REASON, None
                    ),
                )
            )
    return routes


def get_weight(weight: Optional[int], next_hop_ip: Optional[str]) -> Optional[int]:
    if next_hop_ip is None and weight is None:
        # ribd(single-agent) EOS does not provide weight for local routes
        return 0
    else:
        return weight


def _get_as_path(as_path: str) -> Sequence[int]:
    return tuple(map(int, as_path.split()[:-1]))
