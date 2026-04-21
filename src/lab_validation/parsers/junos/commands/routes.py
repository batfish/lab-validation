import json
from collections.abc import Sequence
from typing import Any

from ..models.routes import JunosEvpnRoute, JunosMainRibRoute
from .utils import _parse_table_header, remove_unused_lines

# keys in the json object
ACTIVE_TAG = "active-tag"
DATA = "data"
BGP = "BGP"
MED = "med"
METRIC = "metric"
NH = "nh"
NH_LOCAL_INTERFACE = "nh-local-interface"
PREFERENCE = "preference"
PROTOCOL_NAME = "protocol-name"
RT_ENTRY = "rt-entry"
RT_DESTINATION = "rt-destination"
RT = "rt"
ROUTE_TABLE = "route-table"
ROUTE_INFORMATION = "route-information"
TABLE_NAME = "table-name"
TO = "to"
VIA = "via"


def parse_show_route_display_json(text: str) -> Sequence[JunosMainRibRoute]:
    json_obj = json.loads(remove_unused_lines(text))
    assert ROUTE_INFORMATION in json_obj
    junos_routes: list[JunosMainRibRoute] = []
    for rib in json_obj[ROUTE_INFORMATION]:
        assert ROUTE_TABLE in rib
        for table in rib[ROUTE_TABLE]:
            assert TABLE_NAME in table
            assert len(table[TABLE_NAME]) == 1
            vrf, rib = _parse_table_header(table[TABLE_NAME][0][DATA])
            if rib not in ("inet.0",):
                continue
            junos_routes += _get_routes(vrf, table[RT])

    return junos_routes


def _get_routes(vrf: str, route_json_obj: list[Any]) -> list[JunosMainRibRoute]:
    junos_routes: list[JunosMainRibRoute] = []
    for route in route_json_obj:
        assert RT_DESTINATION in route
        assert len(route[RT_DESTINATION]) == 1
        network = route[RT_DESTINATION][0][DATA]
        for entry in route[RT_ENTRY]:
            assert ACTIVE_TAG in entry
            assert PROTOCOL_NAME in entry
            assert len(entry[PROTOCOL_NAME]) == 1
            assert PREFERENCE in entry
            assert len(entry[PREFERENCE]) == 1
            active = convert_active(entry[ACTIVE_TAG][0].get(DATA, None))
            protocol = entry[PROTOCOL_NAME][0][DATA]
            admin = entry[PREFERENCE][0][DATA]
            metric = (
                entry.get(MED, [{}])[0].get(DATA, None)
                if protocol == BGP
                else entry.get(METRIC, [{}])[0].get(DATA, None)
            )

            nh_type = None
            if NH in entry:
                for nh in entry[NH]:
                    assert TO not in nh or len(nh[TO]) == 1
                    nh_int_key = NH_LOCAL_INTERFACE if protocol == "Local" else VIA
                    assert nh_int_key in nh and len(nh.get(nh_int_key)) == 1
                    next_hop_int = nh.get(nh_int_key)[0][DATA]
                    next_hop_ip = nh.get(TO, [{}])[0].get(DATA, None)

                    junos_routes.append(
                        JunosMainRibRoute(
                            network=network,
                            vrf=vrf,
                            protocol=protocol,
                            admin=admin,
                            next_hop_ip=next_hop_ip,
                            next_hop_int=next_hop_int,
                            metric=metric,
                            nh_type=nh_type,
                            active=active,
                        )
                    )
            else:
                # Handling static null & aggregate routes
                #   Discard - represents static null route
                #   Reject - represents aggregate route

                assert "nh-type" in entry
                nh_type = entry["nh-type"][0]["data"]

                junos_routes.append(
                    JunosMainRibRoute(
                        network=network,
                        vrf=vrf,
                        protocol=protocol,
                        admin=admin,
                        next_hop_ip=None,
                        next_hop_int=None,
                        metric=metric,
                        nh_type=nh_type,
                        active=active,
                    )
                )

    return junos_routes


def parse_show_route_evpn_display_json(text: str) -> Sequence[JunosEvpnRoute]:
    """Parse EVPN routes from show route | display json output.

    Only parses from bgp.evpn.0 table (the global EVPN RIB) to avoid
    double-counting routes that appear in per-VRF evpn.0 tables.
    """
    json_obj = json.loads(remove_unused_lines(text))
    assert ROUTE_INFORMATION in json_obj
    evpn_routes: list[JunosEvpnRoute] = []
    for rib in json_obj[ROUTE_INFORMATION]:
        assert ROUTE_TABLE in rib
        for table in rib[ROUTE_TABLE]:
            assert TABLE_NAME in table
            assert len(table[TABLE_NAME]) == 1
            vrf, rib_name = _parse_table_header(table[TABLE_NAME][0][DATA])
            if rib_name != "bgp.evpn.0":
                continue
            evpn_routes += _get_evpn_routes(table.get(RT, []))
    return evpn_routes


def _parse_evpn_type5_destination(dest: str) -> tuple[str, str] | None:
    """Parse EVPN Type 5 destination into (RD, network).

    Format: 5:<RD>::0::<prefix>::<len>
    Example: 5:172.16.0.100:10000::0::192.168.99.0::24
    Returns: ("172.16.0.100:10000", "192.168.99.0/24")
    """
    if not dest.startswith("5:"):
        return None
    parts = dest.split("::")
    if len(parts) < 4:
        return None
    rd = parts[0][2:]  # strip "5:"
    prefix = parts[2]
    prefix_len = parts[3]
    return rd, f"{prefix}/{prefix_len}"


def _get_evpn_routes(route_json_obj: list[Any]) -> list[JunosEvpnRoute]:
    evpn_routes: list[JunosEvpnRoute] = []
    for route in route_json_obj:
        assert RT_DESTINATION in route
        assert len(route[RT_DESTINATION]) == 1
        dest = route[RT_DESTINATION][0][DATA]
        parsed = _parse_evpn_type5_destination(dest)
        if parsed is None:
            continue
        rd, network = parsed

        for entry in route[RT_ENTRY]:
            assert ACTIVE_TAG in entry
            assert PROTOCOL_NAME in entry
            assert PREFERENCE in entry
            active = convert_active(entry[ACTIVE_TAG][0].get(DATA, None))
            if not active:
                continue
            protocol = entry[PROTOCOL_NAME][0][DATA]
            admin = entry[PREFERENCE][0][DATA]
            as_path_str = entry.get("as-path", [{}])[0].get(DATA, "")
            as_path, origin_type = _parse_as_path_with_origin(as_path_str)
            local_preference = entry.get("local-preference", [{}])[0].get(DATA, None)

            next_hop_ip = None
            next_hop_int = None
            if NH in entry:
                for nh in entry[NH]:
                    next_hop_ip = nh.get(TO, [{}])[0].get(DATA, None)
                    via_key = VIA if VIA in nh else NH_LOCAL_INTERFACE
                    if via_key in nh:
                        next_hop_int = nh[via_key][0][DATA]

            evpn_routes.append(
                JunosEvpnRoute(
                    network=network,
                    route_distinguisher=rd,
                    vrf="default",
                    protocol=protocol,
                    next_hop_ip=next_hop_ip,
                    next_hop_int=next_hop_int,
                    active=active,
                    admin=admin,
                    local_preference=local_preference,
                    as_path=as_path,
                    origin_type=origin_type,
                )
            )
    return evpn_routes


def _parse_as_path_with_origin(as_path_str: str) -> tuple[tuple[int, ...], str]:
    """Parse AS path string containing both path and origin type."""
    if not as_path_str.strip():
        return ((), "I")
    parts = as_path_str.split()
    if parts and parts[-1] in ("I", "E", "?"):
        origin = parts[-1]
        as_nums = parts[:-1]
    else:
        origin = "I"
        as_nums = parts
    try:
        return (tuple(int(x) for x in as_nums if x), origin)
    except ValueError:
        return ((), origin)


def convert_active(active_tag: str | None) -> bool:
    # * = active for both routing and forwarding
    # @ = routing use only (EVPN contributes to routing table but not FIB)
    # # = forwarding use only
    if active_tag in ("*", "@", "#"):
        return True
    elif active_tag is None:
        return False
    else:
        raise Exception(f"'{active_tag}' is not expected active tag")
