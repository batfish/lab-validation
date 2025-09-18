import json
from collections.abc import Sequence
from typing import Any

from ..commands.utils import _parse_table_header, remove_unused_lines
from ..models.routes import JunosBgpRoute

# keys in the json object
LOCAL_PREFERENCE = "local-preference"
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
AS_PATH = "as-path"


def parse_show_route_protocol_bgp_display_json(text: str) -> Sequence[JunosBgpRoute]:
    json_obj = json.loads(remove_unused_lines(text))
    assert ROUTE_INFORMATION in json_obj
    bgp_routes: list[JunosBgpRoute] = []
    for rib in json_obj[ROUTE_INFORMATION]:
        assert ROUTE_TABLE in rib
        for table in rib[ROUTE_TABLE]:
            assert TABLE_NAME in table
            assert len(table[TABLE_NAME]) == 1
            vrf, rib = _parse_table_header(table[TABLE_NAME][0][DATA])
            # skip ipv6
            if rib == "inet6.0":
                continue
            bgp_routes += _get_routes(vrf, table.get(RT, []))

    return bgp_routes


def _get_routes(vrf: str, route_json_obj: list[Any]) -> list[JunosBgpRoute]:
    bgp_routes: list[JunosBgpRoute] = []
    for route in route_json_obj:
        assert RT_DESTINATION in route
        assert len(route[RT_DESTINATION]) == 1
        network = route[RT_DESTINATION][0][DATA]
        for entry in route[RT_ENTRY]:
            assert ACTIVE_TAG in entry
            assert PROTOCOL_NAME in entry and len(entry[PROTOCOL_NAME]) == 1
            assert entry[PROTOCOL_NAME][0][DATA] == "BGP"
            assert PREFERENCE in entry and len(entry[PREFERENCE]) == 1
            assert NH in entry
            assert AS_PATH in entry and len(entry[AS_PATH]) == 1
            assert LOCAL_PREFERENCE in entry and len(entry[LOCAL_PREFERENCE]) == 1

            active_tag = convert_active(entry[ACTIVE_TAG][0].get(DATA, None))
            protocol = entry[PROTOCOL_NAME][0][DATA]
            preference = entry[PREFERENCE][0][DATA]
            metric = entry.get(MED, [{}])[0].get(DATA, None)
            as_path_str = entry[AS_PATH][0][DATA]
            local_pref = entry[LOCAL_PREFERENCE][0][DATA]

            for nh in entry[NH]:
                assert TO not in nh or len(nh[TO]) == 1
                assert VIA in nh and len(nh[VIA]) == 1
                next_hop_int = nh[VIA][0][DATA]
                next_hop_ip = nh[TO][0][DATA]
                as_path, origin_type = _get_as_path(as_path_str)

                bgp_routes.append(
                    JunosBgpRoute(
                        network=network,
                        vrf=vrf,
                        is_active=active_tag,
                        preference=preference,
                        origin_protocol=protocol,
                        next_hop_ip=next_hop_ip,
                        next_hop_int=next_hop_int,
                        metric=metric,
                        local_preference=local_pref,
                        as_path=as_path,
                        origin_type=origin_type,
                    )
                )
    return bgp_routes


def _get_as_path(as_path_str: str) -> tuple[Sequence[int], str]:
    """Extract the AS Path from a string containing both AS Path and origin type."""
    split = as_path_str.split()
    as_path_list, origin_type = split[:-1], split[-1]
    assert origin_type in {"I", "E", "?"}
    as_path = tuple(map(int, as_path_list))
    return (as_path, origin_type)


def convert_active(active_tag: str | None) -> bool:
    if active_tag == "*":
        # active route will have tag *
        return True
    elif active_tag is None:
        # inactive route will have tag None
        return False
    else:
        raise Exception(f"'{active_tag}' is not expected active tag")
