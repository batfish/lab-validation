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
    # An empty object ({}) is the valid response for an instance with no route
    # table — e.g. the vprn "red" state path probed on every SR OS collection
    # when no such VPRN is configured — and yields no routes.
    if not obj:
        return []
    assert _UNICAST in obj, f"missing '{_UNICAST}' in route-table state"
    ipv4 = obj[_UNICAST].get("ipv4", {})
    routes: list[SrosIpRoute] = []
    for entry in ipv4.get("route", []):
        routes.extend(_parse_routes(entry, vrf, if_index_to_name or {}))
    return routes


def _parse_routes(
    entry: dict[str, Any], vrf: str, if_index_to_name: dict[int, str]
) -> Sequence[SrosIpRoute]:
    """One SrosIpRoute per installed next-hop.

    A route has one or more next-hops; multiple equal-cost next-hops are an ECMP
    route, which Batfish represents as one route per next-hop, so emit one
    SrosIpRoute per next-hop to compare like-for-like. The nexthop may carry an
    IP (BGP), an egress if-index (connected/local), or both (resolved
    static/IGP); a blackhole carries neither, yielding a single route with no
    next-hop.
    """
    prefix = entry["ipv4-prefix"]
    protocol = entry["protocol"]
    preference = entry.get("preference")
    nexthops = entry.get("nexthop", [])
    if not nexthops:
        return [
            SrosIpRoute(
                network=prefix,
                vrf=vrf,
                protocol=protocol,
                next_hop_ip=None,
                next_hop_interface=None,
                preference=preference,
                metric=None,
            )
        ]
    routes: list[SrosIpRoute] = []
    for nh in nexthops:
        if_index = nh.get("if-index")
        routes.append(
            SrosIpRoute(
                network=prefix,
                vrf=vrf,
                protocol=protocol,
                next_hop_ip=nh.get("nexthop-ip"),
                next_hop_interface=(
                    if_index_to_name.get(if_index) if if_index is not None else None
                ),
                preference=preference,
                metric=nh.get("metric"),
            )
        )
    return routes
