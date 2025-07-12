from typing import List

import pandas as pd
from pybatfish.datamodel.answer import TableAnswer

from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import (
    BgpRibRoute,
    EvpnRibRoute,
    MainRibRoute,
)


def get_batfish_interfaces(
    interface_properties: TableAnswer, node: str
) -> List[InterfaceProperties]:
    """Extract all interface properties for the given node and convert them into InterfaceProperties."""
    return list(
        InterfaceProperties(
            name=r["Interface"]["interface"],
            access_vlan=r["Access_VLAN"],
            active=r["Active"],
            all_prefixes=r.get("All_Prefixes", []),
            allowed_vlans=r["Allowed_VLANs"],
            bandwidth=r["Bandwidth"],
            description=r["Description"],
            native_vlan=r["Native_VLAN"],
            mtu=r["MTU"],
            speed=r["Speed"],
            switchport=r["Switchport"],
            switchport_mode=r["Switchport_Mode"],
            vrf=r["VRF"],
        )
        for r in interface_properties.rows
        if (
            node == r["Interface"]["hostname"]
            # Skip generated tenant VRF L3 VNI interfaces
            and not r["Interface"]["interface"].startswith("nve~")
        )
    )


def get_batfish_main_rib_routes(
    routes_answer: pd.DataFrame, node: str
) -> List[MainRibRoute]:
    """Extract main rib routes for the given node and convert them into MainRibRoutes."""
    node_routes = routes_answer[routes_answer.Node == node]
    return node_routes.apply(
        lambda r: MainRibRoute(
            network=r["Network"],
            vrf=r["VRF"],
            next_hop=r["Next_Hop"],
            protocol=r["Protocol"],
            metric=r["Metric"],
            admin=r["Admin_Distance"],
            tag=r["Tag"],
        ),
        axis=1,
    ).values.tolist()


def get_batfish_bgp_routes(routes_answer: pd.DataFrame, node: str) -> List[BgpRibRoute]:
    """Extract BGP routes for the given node and convert them into BgpRibRoutes."""
    node_routes = routes_answer[routes_answer.Node == node]
    return node_routes.apply(
        lambda r: BgpRibRoute(
            vrf=r["VRF"],
            network=r["Network"],
            next_hop=r["Next_Hop"],
            next_hop_ip=r["Next_Hop_IP"],
            next_hop_int=r["Next_Hop_Interface"],
            protocol=r["Protocol"],
            as_path=r.get("AS_Path", []),
            metric=r["Metric"],
            local_preference=r["Local_Pref"],
            communities=r.get("Communities", []),
            origin_protocol=r.get("Origin_Protocol"),
            origin_type=r["Origin_Type"],
            weight=r["Weight"],
            tag=r.get("Tag"),
        ),
        axis=1,
    ).values.tolist()


def get_batfish_evpn_routes(
    routes_answer: pd.DataFrame, node: str
) -> List[EvpnRibRoute]:
    """Extract EVPN routes for the given node and convert them into EvpnRibRoutes."""
    node_routes = routes_answer[routes_answer.Node == node]
    return node_routes.apply(
        lambda r: EvpnRibRoute(
            vrf=r["VRF"],
            network=r["Network"],
            route_distinguisher=r["Route_Distinguisher"],
            next_hop=r["Next_Hop"],
            next_hop_ip=r["Next_Hop_IP"],
            next_hop_int=r["Next_Hop_Interface"],
            protocol=r["Protocol"],
            as_path=r.get("AS_Path", []),
            metric=r["Metric"],
            local_preference=r["Local_Pref"],
            communities=tuple(r.get("Communities", [])),
            origin_protocol=r.get("Origin_Protocol"),
            origin_type=r["Origin_Type"],
            tag=r.get("Tag"),
        ),
        axis=1,
    ).values.tolist()
