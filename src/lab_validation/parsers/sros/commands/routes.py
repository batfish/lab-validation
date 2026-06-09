import json
from collections.abc import Sequence
from typing import Any

from ..models.routes import SrosIpRoute

# Top-level key in `info json /state router "Base" route-table` output.
_UNICAST = "nokia-state:unicast"


def parse_route_table_json(
    text: str, vrf: str, if_index_to_name: dict[int, str] | None = None
) -> Sequence[SrosIpRoute]:
    """Parse ``info json /state router "Base" route-table`` into SrosIpRoutes.

    Only the IPv4 unicast table is modeled (the lab is IPv4-only); the IPv6
    table is present but skipped. ``vrf`` is the Batfish VRF name to tag the
    routes with (the SR OS "Base" instance maps to Batfish's "default" VRF).
    ``if_index_to_name`` maps a route nexthop's ``if-index`` to the egress
    interface name (from the interface state); when provided, the next-hop
    interface is resolved so it can be validated, not just the next-hop IP.

    The route-table state entry carries prefix, protocol, preference, flags, and
    the nexthop list (ip / if-index / metric); it does NOT carry a route ``tag``
    leaf, so tag is not modeled. Add it here if SR OS later exposes it (e.g. on a
    tagged static or redistributed route) and a lab exercises it.
    """
    obj = json.loads(text)
    assert _UNICAST in obj, f"missing '{_UNICAST}' in route-table state"
    ipv4 = obj[_UNICAST].get("ipv4", {})
    routes: list[SrosIpRoute] = []
    for entry in ipv4.get("route", []):
        routes.append(_parse_route(entry, vrf, if_index_to_name or {}))
    return routes


def _parse_route(
    entry: dict[str, Any], vrf: str, if_index_to_name: dict[int, str]
) -> SrosIpRoute:
    # A route has one or more next-hops; SR OS does not ECMP in this lab, so the
    # first next-hop carries the metric and (for non-local routes) the next-hop IP.
    # The nexthop may carry an IP (BGP), an egress if-index (connected/local), or
    # both (resolved static/IGP); a blackhole carries neither.
    nexthops = entry.get("nexthop", [])
    next_hop_ip = None
    next_hop_interface = None
    metric = None
    if nexthops:
        nh = nexthops[0]
        next_hop_ip = nh.get("nexthop-ip")
        metric = nh.get("metric")
        if_index = nh.get("if-index")
        if if_index is not None:
            next_hop_interface = if_index_to_name.get(if_index)
    return SrosIpRoute(
        network=entry["ipv4-prefix"],
        vrf=vrf,
        protocol=entry["protocol"],
        next_hop_ip=next_hop_ip,
        next_hop_interface=next_hop_interface,
        preference=entry.get("preference"),
        metric=metric,
    )
