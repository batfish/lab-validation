import json
from collections.abc import Sequence
from typing import Any

from ..models.routes import SrosIpRoute

# Top-level key in `info json /state router "Base" route-table` output.
_UNICAST = "nokia-state:unicast"


def parse_route_table_json(text: str, vrf: str) -> Sequence[SrosIpRoute]:
    """Parse ``info json /state router "Base" route-table`` into SrosIpRoutes.

    Only the IPv4 unicast table is modeled (the lab is IPv4-only); the IPv6
    table is present but skipped. ``vrf`` is the Batfish VRF name to tag the
    routes with (the SR OS "Base" instance maps to Batfish's "default" VRF).
    """
    obj = json.loads(text)
    assert _UNICAST in obj, f"missing '{_UNICAST}' in route-table state"
    ipv4 = obj[_UNICAST].get("ipv4", {})
    routes: list[SrosIpRoute] = []
    for entry in ipv4.get("route", []):
        routes.append(_parse_route(entry, vrf))
    return routes


def _parse_route(entry: dict[str, Any], vrf: str) -> SrosIpRoute:
    # A route has one or more next-hops; SR OS does not ECMP in this lab, so the
    # first next-hop carries the metric and (for non-local routes) the next-hop IP.
    nexthops = entry.get("nexthop", [])
    next_hop_ip = None
    metric = None
    if nexthops:
        nh = nexthops[0]
        next_hop_ip = nh.get("nexthop-ip")
        metric = nh.get("metric")
    return SrosIpRoute(
        network=entry["ipv4-prefix"],
        vrf=vrf,
        protocol=entry["protocol"],
        next_hop_ip=next_hop_ip,
        preference=entry.get("preference"),
        metric=metric,
    )
