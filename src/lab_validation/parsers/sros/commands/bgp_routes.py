import json
from collections.abc import Sequence
from typing import Any

from ..models.routes import SrosBgpRoute

# Top-level keys in `info json /state router "Base" bgp rib` output.
_IPV4_UNICAST = "nokia-state:ipv4-unicast"
_ATTR_SETS = "nokia-state:attr-sets"


def parse_bgp_rib_json(text: str, vrf: str) -> Sequence[SrosBgpRoute]:
    """Parse the local RIB from ``info json /state router "Base" bgp rib``.

    Models the IPv4-unicast BGP local RIB. Each route carries an ``attr-id``
    referencing an entry in the top-level ``attr-sets`` table, which holds the
    full path-attribute set (origin, next-hop, MED, local-pref, AS-path,
    standard/extended/large communities, clusters, prefix-sid, ...). We join
    origin/next-hop/MED/AS-path/communities here. Only the ``ipv4-unicast``
    AFI/SAFI is modeled (the lab is IPv4-unicast); ``label-ipv4`` is skipped.
    """
    return _parse_rib_view(text, vrf, "local-rib")


def parse_bgp_rib_out_json(text: str, vrf: str) -> Sequence[SrosBgpRoute]:
    """Parse the *advertised* routes (``rib-in-out`` / ``rib-out-post``).

    This is the route as advertised to a peer, after the export policy — so its
    attr-set carries the policy-set attributes (community, MED, prepended
    AS-path). It lets us validate SR OS's advertised attributes directly on the
    SR OS side, not only via the receiving peer.
    """
    return _parse_rib_view(text, vrf, "rib-out-post", parent="rib-in-out")


def _parse_rib_view(
    text: str, vrf: str, view: str, parent: str | None = None
) -> Sequence[SrosBgpRoute]:
    obj = json.loads(text)
    # When BGP is not configured on the router, `info json /state ... bgp rib`
    # returns an empty JSON array (no ipv4-unicast/attr-sets objects at all).
    # That is a valid "no BGP routes" state, not a parse error.
    if not obj:
        return []
    assert _IPV4_UNICAST in obj, f"missing '{_IPV4_UNICAST}' in bgp rib"
    attr_sets = _parse_attr_sets(obj.get(_ATTR_SETS, {}))

    container = obj[_IPV4_UNICAST]
    if parent is not None:
        container = container.get(parent, {})
    rib = container.get(view, {})

    routes: list[SrosBgpRoute] = []
    for entry in rib.get("routes", []):
        attrs = attr_sets.get(entry["attr-id"], {})
        # rib-out-post entries carry next-hop on the route, not the attr-set; and
        # they have no owner/used/valid/best flags (they are what we advertise).
        next_hop = entry.get("next-hop", attrs.get("next-hop"))
        routes.append(
            SrosBgpRoute(
                network=entry["prefix"],
                vrf=vrf,
                owner=entry.get("owner", "bgp"),
                neighbor=entry["neighbor"],
                next_hop_ip=next_hop,
                origin_type=attrs.get("origin", ""),
                med=attrs.get("med"),
                as_path=_parse_as_path(attrs.get("as-path")),
                communities=_parse_communities(attrs.get("communities")),
                used=entry.get("used-route", False),
                valid=entry.get("valid-route", False),
                best=entry.get("best-route", False),
                rib_view=view,
            )
        )
    return routes


def _parse_attr_sets(attr_sets_obj: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index the attr-set list by its ``index`` (the attr-id routes reference)."""
    result: dict[str, dict[str, Any]] = {}
    for attr_set in attr_sets_obj.get("attr-set", []):
        result[attr_set["index"]] = attr_set
    return result


# SR OS renders the well-known BGP communities by their symbolic names, while
# Batfish renders them in numeric form. Canonicalize SR OS -> numeric so the two
# sides compare equal regardless of how each emits them (mirrors the Junos
# community canonicalization in #178). An unknown symbolic name raises so a
# contributor adds the mapping rather than masking a real mismatch.
_WELL_KNOWN_COMMUNITIES = {
    "no-export": "65535:65281",
    "no-advertise": "65535:65282",
    "no-export-subconfed": "65535:65283",
    "no-peer": "65535:65284",
}


def _canonicalize_community(value: str) -> str:
    """Map an SR OS symbolic well-known community to its numeric form, else pass through."""
    if ":" in value:
        return value
    canonical = _WELL_KNOWN_COMMUNITIES.get(value)
    assert canonical is not None, (
        f"unknown SR OS symbolic community '{value}'; add it to"
        " _WELL_KNOWN_COMMUNITIES so it compares against Batfish's numeric form"
    )
    return canonical


def _parse_communities(communities_obj: dict[str, Any] | None) -> Sequence[str]:
    """The standard community values (e.g. ``65001:100``) on an attr-set.

    SR OS nests them as ``communities`` -> ``community`` [ {community-value} ].
    Well-known communities are rendered symbolically (e.g. ``no-export``) and are
    canonicalized to their numeric form to match Batfish. Extended/large/
    ipv6-extended communities live in sibling containers (``extended-communities``
    etc.) and can be added the same way when modeled.
    """
    if not communities_obj:
        return ()
    return tuple(
        _canonicalize_community(c["community-value"])
        for c in communities_obj.get("community", [])
        if "community-value" in c
    )


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
