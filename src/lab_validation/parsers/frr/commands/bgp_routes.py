import json
from collections.abc import Sequence
from typing import Any

from ..models.routes import FrrBgpRoute, FrrBgpRouteNextHop

AFI = "afi"
ASPATH = "aspath"
BESTPATH = "bestpath"
IP = "ip"
MED = "med"
MULTIPATH = "multipath"
NEXTHOPS = "nexthops"
ORIGIN = "origin"
PATH_FROM = "pathFrom"
PEER_ID = "peerId"
ROUTES = "routes"
SCOPE = "scope"
USED = "used"
VALID = "valid"
WEIGHT = "weight"


def parse_show_ip_bgp_vrf_all_json(text: str) -> Sequence[FrrBgpRoute]:
    json_obj = json.loads(text)
    routes: list[FrrBgpRoute] = []
    for vrf_name in json_obj:
        if ROUTES in json_obj[vrf_name]:
            routes += _get_bgp_routes(vrf_name, json_obj[vrf_name][ROUTES])
    return routes


def _get_bgp_routes(vrf: str, json_obj: dict[Any, Any]) -> Sequence[FrrBgpRoute]:
    routes: list[FrrBgpRoute] = []
    for network in json_obj:
        routes_obj = json_obj[network]

        for path in routes_obj:
            assert ASPATH in path
            assert NEXTHOPS in path
            assert ORIGIN in path
            assert PATH_FROM in path
            assert PEER_ID in path
            assert WEIGHT in path
            assert VALID in path

            routes.append(
                FrrBgpRoute(
                    vrf=vrf,
                    network=network,
                    is_valid=path[VALID],
                    is_bestpath=path.get(BESTPATH, False),
                    is_multipath=path.get(MULTIPATH, False),
                    origin=path[ORIGIN],
                    path_from=path[PATH_FROM],
                    peer_id=path[PEER_ID],
                    as_path=_get_as_path(path[ASPATH]),
                    med=path.get(MED, None),
                    weight=path[WEIGHT],
                    next_hops=_get_next_hops(path[NEXTHOPS]),
                )
            )
    return routes


def _get_as_path(as_path: str) -> Sequence[int]:
    return tuple(map(int, as_path.split()))


def _get_next_hops(json_obj: list[dict[Any, Any]]) -> Sequence[FrrBgpRouteNextHop]:
    next_hops: list[FrrBgpRouteNextHop] = []
    for next_hop in json_obj:
        assert IP in next_hop
        assert AFI in next_hop

        next_hops.append(
            FrrBgpRouteNextHop(
                ip=next_hop[IP],
                afi=next_hop[AFI],
                scope=next_hop.get(SCOPE, None),
                is_used=next_hop.get(USED, False),
            )
        )

    return next_hops
