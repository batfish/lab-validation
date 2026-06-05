import json
from collections.abc import Sequence
from typing import Any

from ..models.routes import SrosBgpRoute

# Top-level keys in `info json /state router "Base" bgp rib` output.
_IPV4_UNICAST = "nokia-state:ipv4-unicast"
_ATTR_SETS = "nokia-state:attr-sets"


def parse_bgp_rib_json(text: str, vrf: str) -> Sequence[SrosBgpRoute]:
    """Parse ``info json /state router "Base" bgp rib`` into SrosBgpRoutes.

    Models the IPv4-unicast BGP local RIB. Each route carries an ``attr-id``
    referencing an entry in the top-level ``attr-sets`` table, which holds the
    origin, next-hop, MED, and AS-path; we join them here. Only the
    ``ipv4-unicast`` AFI/SAFI is modeled (the lab is IPv4-unicast eBGP); the
    ``label-ipv4`` table is skipped.
    """
    obj = json.loads(text)
    assert _IPV4_UNICAST in obj, f"missing '{_IPV4_UNICAST}' in bgp rib"
    attr_sets = _parse_attr_sets(obj.get(_ATTR_SETS, {}))

    routes: list[SrosBgpRoute] = []
    local_rib = obj[_IPV4_UNICAST].get("local-rib", {})
    for entry in local_rib.get("routes", []):
        attrs = attr_sets.get(entry["attr-id"], {})
        routes.append(
            SrosBgpRoute(
                network=entry["prefix"],
                vrf=vrf,
                owner=entry["owner"],
                neighbor=entry["neighbor"],
                next_hop_ip=attrs.get("next-hop"),
                origin_type=attrs.get("origin", ""),
                med=attrs.get("med"),
                as_path=_parse_as_path(attrs.get("as-path")),
                used=entry["used-route"],
                valid=entry["valid-route"],
                best=entry["best-route"],
            )
        )
    return routes


def _parse_attr_sets(attr_sets_obj: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index the attr-set list by its ``index`` (the attr-id routes reference)."""
    result: dict[str, dict[str, Any]] = {}
    for attr_set in attr_sets_obj.get("attr-set", []):
        result[attr_set["index"]] = attr_set
    return result


def _parse_as_path(as_path_obj: dict[str, Any] | None) -> Sequence[int]:
    """Flatten the SR OS nested as-path (segments -> as-numbers) to a list of ASNs.

    Only as-sequence segments occur in this lab; as-set would need set modeling,
    which we do not yet exercise.
    """
    if not as_path_obj:
        return []
    asns: list[int] = []
    for segment in as_path_obj.get("segment", []):
        for as_number in segment.get("as-numbers", []):
            asns.append(as_number["as-number"])
    return asns
