from collections import defaultdict

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

_VLAN_IFACE_PREFIXES = ("irb.", "vlan")


def get_vni_backed_ifaces(
    interface_properties: TableAnswer, l2_vni_properties: pd.DataFrame
) -> dict[str, set[str]]:
    """Compute the set of VLAN/IRB interface names with VNI backing per node.

    Combines L2 VNIs (from vxlanVniProperties, which provides VLAN numbers
    directly) and L3 VNIs (detected by nve~ interfaces sharing a VRF with a
    VLAN/IRB interface in interfaceProperties).
    """
    # Build L2 VNI VLAN numbers per node
    l2_vlans: dict[str, set[int]] = defaultdict(set)
    for _, row in l2_vni_properties.iterrows():
        l2_vlans[row["Node"]].add(int(row["VLAN"]))

    # Scan interfaceProperties for nve~ VRFs and VLAN/IRB interfaces
    nve_vrfs: dict[str, set[str]] = defaultdict(set)
    ifaces_by_vrf: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for r in interface_properties.rows:
        hostname = r["Interface"]["hostname"]
        iface = r["Interface"]["interface"]
        vrf = r["VRF"]
        if iface.startswith("nve~"):
            nve_vrfs[hostname].add(vrf)
        if iface.lower().startswith(_VLAN_IFACE_PREFIXES):
            ifaces_by_vrf[hostname][vrf].append(iface)

    # Collect VNI-backed interface names
    result: dict[str, set[str]] = defaultdict(set)

    # L2 VNIs: match VLAN number from vxlanVniProperties to interface names.
    # Interface naming: irb.{vlan} (Junos) or Vlan{vlan} (NX-OS/EOS).
    for hostname, vlans in l2_vlans.items():
        for vrf_ifaces in ifaces_by_vrf[hostname].values():
            for iface in vrf_ifaces:
                for vlan in vlans:
                    if iface == f"irb.{vlan}" or iface.lower() == f"vlan{vlan}":
                        result[hostname].add(iface)

    # L3 VNIs: any VLAN/IRB in a VRF that also has an nve~ interface
    for hostname, vrfs in nve_vrfs.items():
        for vrf in vrfs:
            for iface in ifaces_by_vrf[hostname].get(vrf, []):
                result[hostname].add(iface)

    return dict(result)


def get_batfish_interfaces(
    interface_properties: TableAnswer, node: str
) -> list[InterfaceProperties]:
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
) -> list[MainRibRoute]:
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


def get_batfish_bgp_routes(routes_answer: pd.DataFrame, node: str) -> list[BgpRibRoute]:
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
) -> list[EvpnRibRoute]:
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
