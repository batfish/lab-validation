import json
from collections.abc import Sequence
from typing import Any

from ..models.routes import JunosMainRibRoute
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
            # skip ipv6
            if rib == "inet6.0":
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


def convert_active(active_tag: str | None) -> bool:
    if active_tag == "*":
        # active route will have tag *
        return True
    elif active_tag is None:
        # inactive route will have tag None
        return False
    else:
        raise Exception(f"'{active_tag}' is not expected active tag")
