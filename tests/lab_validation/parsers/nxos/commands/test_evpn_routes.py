from lab_validation.parsers.nxos.commands.evpn_routes import (
    _extract_ip_network,
    parse_show_bgp_l2vpn_evpn,
)
from lab_validation.parsers.nxos.models.routes import NxosEvpnRoute

_L2VNI_HEADER = """\
BGP routing table information for VRF default, address family L2VPN EVPN
BGP table version is 23, Local Router ID is 1.1.1.1
Status: s-suppressed, x-deleted, S-stale, d-dampened, h-history, *-valid, >-best
Path type: i-internal, e-external, c-confed, l-local, a-aggregate, r-redist, I-injected
Origin codes: i - IGP, e - EGP, ? - incomplete, | - multipath, & - backup, 2 - best2

   Network            Next Hop            Metric     LocPrf     Weight Path
"""


class TestExtractIpNetwork:
    def test_type5(self) -> None:
        assert (
            _extract_ip_network("[5]:[0]:[0]:[24]:[192.168.10.0]/224")
            == "192.168.10.0/24"
        )

    def test_type5_host(self) -> None:
        assert _extract_ip_network("[5]:[0]:[0]:[32]:[10.0.0.1]/224") == "10.0.0.1/32"

    def test_type3(self) -> None:
        assert _extract_ip_network("[3]:[0]:[32]:[1.1.1.1]/88") == "1.1.1.1/32"

    def test_type2_with_ip_skipped(self) -> None:
        assert (
            _extract_ip_network(
                "[2]:[0]:[0]:[48]:[0c8e.9b19.2d01]:[32]:[192.168.10.2]/248"
            )
            is None
        )

    def test_type2_mac_only_skipped(self) -> None:
        assert (
            _extract_ip_network("[2]:[0]:[0]:[48]:[0c8e.9b19.2d01]:[0]:[0.0.0.0]/216")
            is None
        )


class TestParseShowBgpL2vpnEvpn:
    def test_type5_routes(self) -> None:
        text = (
            _L2VNI_HEADER
            + """\
Route Distinguisher: 2.2.2.2:3
*>i[5]:[0]:[0]:[24]:[192.168.20.0]/224
                      2.2.2.2                  0        100          0 ?

Route Distinguisher: 1.1.1.1:3    (L3VNI 100777)
*>l[5]:[0]:[0]:[24]:[192.168.10.0]/224
                      1.1.1.1                  0        100      32768 ?
"""
        )
        routes = parse_show_bgp_l2vpn_evpn(text)
        assert routes == [
            NxosEvpnRoute(
                route_distinguisher="2.2.2.2:3",
                network="192.168.20.0/24",
                next_hop_ip="2.2.2.2",
                metric=0,
                local_preference=100,
                weight=0,
                as_path=(),
                best_path=True,
                origin_type="?",
            ),
            NxosEvpnRoute(
                route_distinguisher="1.1.1.1:3",
                network="192.168.10.0/24",
                next_hop_ip="1.1.1.1",
                metric=0,
                local_preference=100,
                weight=32768,
                as_path=(),
                best_path=True,
                origin_type="?",
            ),
        ]

    def test_type3_imet_routes(self) -> None:
        text = (
            _L2VNI_HEADER
            + """\
Route Distinguisher: 1.1.1.1:32777    (L2VNI 5010)
*>l[3]:[0]:[32]:[1.1.1.1]/88
                      1.1.1.1                           100      32768 i
*>i[3]:[0]:[32]:[2.2.2.2]/88
                      2.2.2.2                           100          0 i
"""
        )
        routes = parse_show_bgp_l2vpn_evpn(text)
        assert routes == [
            NxosEvpnRoute(
                route_distinguisher="1.1.1.1:32777",
                network="1.1.1.1/32",
                next_hop_ip="1.1.1.1",
                metric=None,
                local_preference=100,
                weight=32768,
                as_path=(),
                best_path=True,
                origin_type="i",
            ),
            NxosEvpnRoute(
                route_distinguisher="1.1.1.1:32777",
                network="2.2.2.2/32",
                next_hop_ip="2.2.2.2",
                metric=None,
                local_preference=100,
                weight=0,
                as_path=(),
                best_path=True,
                origin_type="i",
            ),
        ]

    def test_type2_routes_skipped(self) -> None:
        """Type 2 (MAC/IP) routes are not modeled by Batfish and should be skipped."""
        text = (
            _L2VNI_HEADER
            + """\
Route Distinguisher: 1.1.1.1:32777    (L2VNI 5010)
*>i[2]:[0]:[0]:[48]:[0c8e.9b19.2d01]:[0]:[0.0.0.0]/216
                      2.2.2.2                           100          0 i
*>l[2]:[0]:[0]:[48]:[0c8e.9ba4.5401]:[32]:[192.168.10.1]/248
                      1.1.1.1                           100      32768 i
*>l[3]:[0]:[32]:[1.1.1.1]/88
                      1.1.1.1                           100      32768 i
"""
        )
        routes = parse_show_bgp_l2vpn_evpn(text)
        assert len(routes) == 1
        assert routes[0].network == "1.1.1.1/32"

    def test_multiple_rd_blocks(self) -> None:
        text = (
            _L2VNI_HEADER
            + """\
Route Distinguisher: 1.1.1.1:3    (L3VNI 100777)
*>l[5]:[0]:[0]:[24]:[192.168.10.0]/224
                      1.1.1.1                  0        100      32768 ?

Route Distinguisher: 2.2.2.2:3
*>i[5]:[0]:[0]:[24]:[192.168.20.0]/224
                      2.2.2.2                  0        100          0 ?
"""
        )
        routes = parse_show_bgp_l2vpn_evpn(text)
        assert len(routes) == 2
        assert routes[0].route_distinguisher == "1.1.1.1:3"
        assert routes[1].route_distinguisher == "2.2.2.2:3"

    def test_route_with_as_path(self) -> None:
        text = (
            _L2VNI_HEADER
            + """\
Route Distinguisher: 10.0.0.1:3
*>e[5]:[0]:[0]:[24]:[172.16.0.0]/224
                      10.0.0.2                 0        100          0 65001 65002 i
"""
        )
        routes = parse_show_bgp_l2vpn_evpn(text)
        assert len(routes) == 1
        assert routes[0].as_path == (65001, 65002)
        assert routes[0].origin_type == "i"

    def test_non_best_path(self) -> None:
        text = (
            _L2VNI_HEADER
            + """\
Route Distinguisher: 1.1.1.1:3
* i[5]:[0]:[0]:[24]:[192.168.10.0]/224
                      1.1.1.1                  0        100          0 ?
"""
        )
        routes = parse_show_bgp_l2vpn_evpn(text)
        assert len(routes) == 1
        assert routes[0].best_path is False

    def test_real_l3vni_data(self) -> None:
        """Parse actual NX-OS L3VNI lab data."""
        text = """\
BGP routing table information for VRF default, address family L2VPN EVPN
BGP table version is 24, Local Router ID is 1.1.1.1
Status: s-suppressed, x-deleted, S-stale, d-dampened, h-history, *-valid, >-best
Path type: i-internal, e-external, c-confed, l-local, a-aggregate, r-redist, I-injected
Origin codes: i - IGP, e - EGP, ? - incomplete, | - multipath, & - backup, 2 - best2

   Network            Next Hop            Metric     LocPrf     Weight Path
Route Distinguisher: 2.2.2.2:3
*>i[5]:[0]:[0]:[24]:[192.168.20.0]/224
                      2.2.2.2                  0        100          0 ?

Route Distinguisher: 1.1.1.1:3    (L3VNI 100777)
*>l[5]:[0]:[0]:[24]:[192.168.10.0]/224
                      1.1.1.1                  0        100      32768 ?"""
        routes = parse_show_bgp_l2vpn_evpn(text)
        assert len(routes) == 2
        assert routes[0] == NxosEvpnRoute(
            route_distinguisher="2.2.2.2:3",
            network="192.168.20.0/24",
            next_hop_ip="2.2.2.2",
            metric=0,
            local_preference=100,
            weight=0,
            as_path=(),
            best_path=True,
            origin_type="?",
        )
        assert routes[1] == NxosEvpnRoute(
            route_distinguisher="1.1.1.1:3",
            network="192.168.10.0/24",
            next_hop_ip="1.1.1.1",
            metric=0,
            local_preference=100,
            weight=32768,
            as_path=(),
            best_path=True,
            origin_type="?",
        )
