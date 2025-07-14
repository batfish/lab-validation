import math
from collections import defaultdict
from os import PathLike, path
from typing import (
    AbstractSet,
    Any,
    DefaultDict,
    Dict,
    MutableSet,
    Sequence,
    Set,
    Text,
    Tuple,
)

from pybatfish.datamodel.route import (
    NextHop,
    NextHopDiscard,
    NextHopInterface,
    NextHopIp,
)

from lab_validation.parsers.junos.commands.bgp_routes import (
    parse_show_route_protocol_bgp_display_json,
)
from lab_validation.parsers.junos.commands.interfaces import parse_show_interfaces_json
from lab_validation.parsers.junos.commands.routes import parse_show_route_display_json
from lab_validation.parsers.junos.models.interfaces import JunosInterface
from lab_validation.parsers.junos.models.routes import JunosBgpRoute, JunosMainRibRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.batfish_models.runtime_data import (
    InterfaceRuntimeData,
    NodeRuntimeData,
)

from .utils.validation_utils import match_pairs, matched_pairs_to_failures
from .vendor_validator import VendorValidator


class JunosValidator(VendorValidator):
    SHOW_ROUTE_FILENAME = "show_route_|_display_json.txt"
    SHOW_BGP_ROUTE_FILENAME = "show_route_protocol_bgp_|_display_json.txt"
    SHOW_INTERFACE_FILENAME = "show_interfaces_|_display_json.txt"

    def __init__(self, device_path: PathLike) -> None:
        self.device_path: PathLike = device_path

    def get_runtime_data(self) -> NodeRuntimeData:
        real_interfaces: Sequence[JunosInterface] = self._parse_interface()
        return NodeRuntimeData(
            interfaces=JunosValidator.get_interface_runtime_data(real_interfaces)
        )

    def validate_main_rib_routes(
        self, batfish_routes: Sequence[MainRibRoute]
    ) -> Dict[Any, Any]:
        """Validating main RIB routes from all VRFs"""
        real_routes: Sequence[JunosMainRibRoute] = self._parse_routes()

        real_routes = [r for r in real_routes if not filter_route(r)]

        matched_routes = match_pairs(
            real_routes,
            batfish_routes,
            _routes_cost,
        )
        return matched_pairs_to_failures(matched_routes)

    def validate_bgp_rib_routes(
        self, batfish_routes: Sequence[BgpRibRoute]
    ) -> Dict[Any, Any]:
        return self._compare_all_bgp_routes(self._parse_bgp_routes(), batfish_routes)

    def validate_interface_properties(
        self, batfish_interfaces: Sequence[InterfaceProperties]
    ) -> Dict[Any, Any]:
        real_interfaces = self._parse_interface()

        diffs: Dict[Any, Any] = {}
        batfish_index = {i.name.lower(): i for i in batfish_interfaces}
        real_index = {i.name.lower(): i for i in real_interfaces}

        # Get the extra interfaces in Batfish
        for name in batfish_index.keys() - real_index.keys():
            diffs[name] = f"Extra interface in Batfish: {batfish_index[name]}"

        # Get the missing interfaces in Batfish
        missing_in_batfish = real_index.keys() - batfish_index.keys()
        for name in missing_in_batfish:
            if not self._exclude_iface(name, missing_in_batfish):
                diffs[name] = f"Missing interface in Batfish: {real_index[name]}"

        # Get the diff for common interfaces
        for name in real_index.keys() & batfish_index.keys():
            diff = JunosValidator._compare_interfaces(
                real_index[name], batfish_index[name]
            )
            if diff:
                diffs[name] = diff
        return diffs

    @staticmethod
    def _exclude_iface(iface_name: Text, missing_in_batfish: Set[Text]) -> bool:
        exclude_iface = {
            # GRE: pseudo interface. Manual configured interfaces will be .1, .2 etc...
            # https://www.juniper.net/documentation/en_US/junos/topics/topic-map/switches-interface-gre.html#id-configuring-a-gre-tunnel
            "gr-0/0/0",
            # Packet forwarding engine: for internal communication between RE and PFE
            "pfe-0/0/0",
            "pfe-0/0/0.16383",
            # PFH interfaces are pseudo/virtual interfaces, which represent the PFE Host Processor. It is used for
            # intra-chassis communication and is not user-configurable.
            # https://kb.juniper.net/InfoCenter/index?page=content&id=KB23578&actp=search
            "pfh-0/0/0",
            "pfh-0/0/0.16383",
            "pfh-0/0/0.16384",
            # backup mgmt interface for virtual chassis
            # https://kb.juniper.net/InfoCenter/index?page=content&id=KB25724&cat=EX6200&actp=LIST
            "bme0",
            "bme0.0",
            # customer backbone port: Manual configured interfaces will be .1, .2 etc...
            # https://www.juniper.net/documentation/en_US/junos/topics/concept/pbb-evpn-integration-for-dci-overview.html
            "cbp0",
            # discard interface
            # https://www.juniper.net/documentation/en_US/junos/topics/topic-map/discard-interfaces.html#id-discard-interfaces-overview
            "dsc",
            # Ethernet Segment Interface: related to EVPN
            # https://www.juniper.net/documentation/en_US/junos/topics/example/evpn-mpls-esi-logical-interfaces.html
            "esi",
            # Internally generated interface that is configurable only as the control channel for Generalized MPLS (
            # GMPLS).
            "gre",
            # IP-over-IP tunnel interface. Internally generated interface that is not configurable. Manual configured
            # interfaces will be .1, .2 etc...
            # https://www.juniper.net/documentation/en_US/junos/topics/topic-map/tunnel-services-overview.html#id
            # -tunnel-services-overview
            "ipip",
            # integrated routing and bridging. L3 interface for inter-vlan routing. Manual configured interfaces will
            # be .1, .2 etc...
            "irb",
            # Related to sFlow monitoring. Internally generated interface that is not configurable.
            "jsrv",
            "jsrv.1",
            # non-configurable interface for router control traffic
            "lo0.16385",
            # label switched interface. Related to VPLS/MPLS. Internally generated interface that is not configurable.
            "lsi",
            # Internally generated interface that is not configurable.
            "mtun",
            # Multicast PIM: Internally generated interface that is not configurable.
            "pimd",
            "pime",
            # provider instance port: Manual configured interfaces will be .1, .2 etc...
            # https://www.juniper.net/documentation/en_US/junos/topics/example/example-pbb-mh-evpn-for-dci-configuring.html
            "pip0",
            # Traffic mirroring interface. Internally generated interface that is not configurable.
            # https://kb.juniper.net/InfoCenter/index?page=content&id=KB34543&cat=SRX_210&actp=LIST
            "tap",
            # Virtual Management Ethernet interface. Manual configured interfaces will be .1, .2 etc...
            # https://www.juniper.net/documentation/en_US/junos/topics/task/configuration/virtual-chassis-ex4200-vme-cli.html
            "vme",
            # Virtual Tunnel Endpoint Port: EVPN. Manual configured interfaces will be .1, .2 etc...
            "vtep",
        }

        if iface_name.startswith("xe"):
            if (
                iface_name.endswith(".16386")
                or f"{iface_name}.16386" in missing_in_batfish
            ):
                """
                Junos creates `xe` interface with ".16386" by default if the interface is not configured explicitly by
                user. When user configures the interface, Junos will replace `.16386` interface with configured unit.
                So, excluding specific interfaces "xe-a/a/a" & "xe-a/a/a.16386".
                Example:
                By Default                  = "xe-0/0/8" & "xe-0/0/8.16386"
                After unit 0 configuration  = "xe-0/0/8" & "xe-0/0/8.0"
                """
                return True
        if iface_name.startswith("em"):
            # Junos displays lot of `em` interfaces in show data. So, excluding `em` interfaces that is not in config
            return True
        if iface_name in exclude_iface:
            """
            Junos 'show interface' displays many internal interfaces that junos creates by default. Batfish does not
            create these interfaces unless it is configured explicitly. Excluding these interfaces. For more info
            related to this interfaces refer below link:
            "https://www.juniper.net/documentation/en_US/junos/topics/topic-map/router-interfaces-overview.html#id#
            -10147130."
            """
            return True
        return False

    @staticmethod
    def _compare_interfaces(
        real_interface: JunosInterface, batfish_interface: InterfaceProperties
    ) -> Dict[Text, Text]:
        diff = {}

        if not batfish_interface.name.startswith("em"):
            # Batfish deactivates management interfaces
            if batfish_interface.active != (
                real_interface.state.admin and real_interface.state.line
            ):
                diff[
                    "active"
                ] = f"Batfish: {batfish_interface.active}, JUNOS: admin={real_interface.state.admin} line={real_interface.state.line}"

        if real_interface.bandwidth is None:
            junos_bw = real_interface.speed
        else:
            junos_bw = real_interface.bandwidth

        if batfish_interface.bandwidth != junos_bw:
            # Skipping loopback interface bw: Junos sets it to `None` and batfish sets 1E12. So we already know it
            # will always disagree.
            if not (
                real_interface.name.startswith("lo0")
                and real_interface.bandwidth is None
            ):
                diff[
                    "bandwidth"
                ] = f"Batfish: {batfish_interface.bandwidth}, JUNOS: {junos_bw}"

        # Ignoring MTU as Batfish does not model it correctly
        # if batfish_if.mtu != junos_interface.mtu:
        #     diff["mtu"] = f"Batfish: {batfish_if.mtu}, JUNOS: {junos_interface.mtu}"

        return diff

    @staticmethod
    def get_interface_runtime_data(
        interfaces: Sequence[JunosInterface],
    ) -> Dict[str, InterfaceRuntimeData]:
        return {
            iface.name: InterfaceRuntimeData(
                bandwidth=iface.bandwidth, lineUp=iface.state.line, speed=iface.speed
            )
            for iface in interfaces
        }

    def _parse_routes(self) -> Sequence[JunosMainRibRoute]:
        show_route_path = path.join(
            self.device_path, JunosValidator.SHOW_ROUTE_FILENAME
        )

        if not path.isfile(show_route_path):
            return []

        with open(show_route_path) as fp:
            routes_text = fp.read()
        return parse_show_route_display_json(routes_text)

    def _parse_bgp_routes(self) -> Sequence[JunosBgpRoute]:
        show_route_path = path.join(
            self.device_path, JunosValidator.SHOW_BGP_ROUTE_FILENAME
        )

        if not path.isfile(show_route_path):
            return []

        with open(show_route_path) as fp:
            routes_text = fp.read()
        return parse_show_route_protocol_bgp_display_json(routes_text)

    def _parse_interface(self) -> Sequence[JunosInterface]:
        show_interface_path = path.join(
            self.device_path, JunosValidator.SHOW_INTERFACE_FILENAME
        )

        if not path.isfile(show_interface_path):
            return []

        with open(show_interface_path) as fp:
            interface_text = fp.read()
        return parse_show_interfaces_json(interface_text)

    def _compare_all_bgp_routes(
        self,
        real_routes: Sequence[JunosBgpRoute],
        batfish_routes: Sequence[BgpRibRoute],
    ) -> Dict[Any, Any]:
        # Group real routes by that key.
        real: DefaultDict[Tuple, MutableSet[JunosBgpRoute]] = defaultdict(set)
        for r in real_routes:
            real[(r.vrf, r.network, r.next_hop_ip)].add(r)

        # Group Batfish routes by that key.
        batfish: DefaultDict[Tuple, MutableSet[BgpRibRoute]] = defaultdict(set)
        for bf_route in batfish_routes:
            batfish[(bf_route.vrf, bf_route.network, bf_route.next_hop_ip)].add(
                bf_route
            )

        common_keys = real.keys() & batfish.keys()
        missing_keys = real.keys() - batfish.keys()
        extra_keys = batfish.keys() - real.keys()

        failures: Dict[Any, Any] = {}
        for k in common_keys:
            diff = JunosValidator._compare_bgp_rib_routes(real[k], batfish[k])
            if len(diff) != 0:
                failures[k] = diff
        for k in missing_keys:
            assert len(real[k]) == 1
            for route in real[k]:
                if route.is_active is False:
                    # Batfish only returns active routes. Skipping inactive routes
                    continue
                failures[k] = "Batfish is missing route: {}".format(real[k])
        for k in extra_keys:
            failures[k] = "Batfish has extra route: {}".format(batfish[k])
        return failures

    @staticmethod
    def _compare_bgp_rib_routes(
        real_routes: AbstractSet[JunosBgpRoute],
        batfish_routes: AbstractSet[BgpRibRoute],
    ) -> Dict[Text, Text]:
        real_route: JunosBgpRoute = next(iter(real_routes))
        batfish_route: BgpRibRoute = next(iter(batfish_routes))
        diff: Dict[Text, Text] = {}
        real_metric = 0 if real_route.metric is None else real_route.metric

        if real_route.is_active is False:
            # Batfish is reporting as active a route that is inactive
            diff["Unexpected_inactive_route"] = f"Batfish: {batfish_route}"

        if batfish_route.metric != real_metric:
            diff["metric"] = "Batfish: {}, real: {}".format(
                batfish_route.metric, real_metric
            )
        if batfish_route.local_preference != real_route.local_preference:
            diff["local_preference"] = "Batfish: {}, real: {}".format(
                batfish_route.local_preference, real_route.local_preference
            )
        if batfish_route.as_path != real_route.as_path:
            diff["as_path"] = "Batfish: {}, real: {}".format(
                batfish_route.as_path, real_route.as_path
            )
        assert batfish_route.origin_protocol is not None
        if batfish_route.origin_protocol.lower() != real_route.origin_protocol.lower():
            diff["origin_protocol"] = "Batfish: {}, real: {}".format(
                batfish_route.origin_protocol, real_route.origin_protocol
            )
        valid_origin_pairs = {("I", "igp"), ("E", "egp"), ("?", "incomplete")}
        if (
            real_route.origin_type,
            batfish_route.origin_type,
        ) not in valid_origin_pairs:
            diff["origin_type"] = "Batfish: {}, real: {}".format(
                batfish_route.origin_type, real_route.origin_type
            )
        return diff


def _routes_cost(
    expected_route: JunosMainRibRoute, batfish_route: MainRibRoute
) -> float:
    """A cost function between Juniper show routes and Batfish routes for the main RIB"""

    # Different networks, different VRFs, are wholly incompatible.
    if expected_route.network != batfish_route.network:
        return math.inf
    if expected_route.vrf != batfish_route.vrf:
        return math.inf

    cost = 0.0

    cost += _compute_protocol_cost(expected_route, batfish_route)
    cost += _compute_nexthop_cost(expected_route, batfish_route.next_hop)

    if (expected_route.metric or 0) != batfish_route.metric:
        cost += 1.0
    if expected_route.admin != batfish_route.admin:
        cost += 1.0

    return cost


def _compute_protocol_cost(
    expected_route: JunosMainRibRoute, batfish_route: MainRibRoute
) -> float:
    if expected_route.protocol == "Direct":
        if batfish_route.protocol == "connected":
            return 0.0
        return math.inf
    if expected_route.protocol == "Local":
        if batfish_route.protocol == "local":
            return 0.0
        return math.inf
    if expected_route.protocol == "Aggregate":
        if batfish_route.protocol == "aggregate":
            return 0.0
        return math.inf
    if expected_route.protocol == "Static":
        if batfish_route.protocol == "static":
            return 0.0
        return math.inf
    if expected_route.protocol == "BGP":
        if batfish_route.protocol in {"bgp", "ibgp"}:
            return 0.0
        return math.inf
    if expected_route.protocol == "OSPF":
        if batfish_route.protocol in {"ospf", "ospfE1", "ospfE2", "ospfIA", "ospfIS"}:
            return 0.0
        return math.inf

    return math.inf


def _is_mgmt_iface(junos_name: str | None) -> bool:
    """Return true iff Batfish treats this interface as a management interface."""
    if junos_name is None:
        return False
    return junos_name.startswith("em0")


def _compute_nexthop_cost(
    expected_route: JunosMainRibRoute, next_hop: NextHop
) -> float:
    if _is_mgmt_iface(expected_route.next_hop_int) and isinstance(
        next_hop, NextHopDiscard
    ):
        # Batfish creates null discard routes for down management interfaces.
        return 0.0

    if expected_route.nh_type in {"Discard", "Reject"} and isinstance(
        next_hop, NextHopDiscard
    ):
        return 0.0
    elif expected_route.nh_type in {"Discard", "Reject"} or isinstance(
        next_hop, NextHopDiscard
    ):
        # Only one is null-routed.
        return 10.0

    if isinstance(next_hop, NextHopIp):
        if expected_route.protocol == "Static":
            # For static nhip-only routes, Batfish shows protocol nhip, while junos shows resolved nhip
            return 0.0
        elif expected_route.next_hop_ip == next_hop.ip:
            return 0.0
        else:
            return 1.0

    if isinstance(next_hop, NextHopInterface):
        cost = 0.0
        if expected_route.next_hop_int != next_hop.interface:
            cost += 5.0
        if next_hop.ip is not None and expected_route.next_hop_ip != next_hop.ip:
            cost += 1.0
        return cost

    raise ValueError("Unsupported next hop " + repr(next_hop))


def filter_route(real_route: JunosMainRibRoute) -> bool:
    # Juniper throws in a multicast route when you're using OSPF, filter it out
    if real_route.network.startswith("224.0.0") and real_route.nh_type == "MultiRecv":
        return True
    # em0.0 is junos dedicated mgmt interface
    elif _is_mgmt_iface(real_route.next_hop_int):
        # Junos creates local /32 for down interfaces,
        # and so does Batfish.
        return not real_route.network.endswith("/32")
    # batfish creates only active routes
    elif not real_route.active:
        return True
    else:
        return False
