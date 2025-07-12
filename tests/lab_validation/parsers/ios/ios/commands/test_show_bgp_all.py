from lab_validation.parsers.ios.commands.show_bgp_all import (
    _af_table_routes_vrf,
    parse_show_bgp_all,
)
from lab_validation.parsers.ios.models.bgp import (
    IosBgpAddressFamily,
    IosBgpRoute,
    IosBgpVrf,
)


def test_parsing() -> None:
    records = parse_show_bgp_all(
        """For address family: IPv4 Unicast

BGP table version is 21, local router ID is 192.168.123.2
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter,
              x best-external, a additional-path, c RIB-compressed,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 r>  10.10.10.0/24    10.10.10.1               0             0 1 i
 *>  192.168.122.0    10.10.10.1               0             0 1 i
 *>  192.168.123.1/32 10.10.10.1               0             0 1 i
 *>  192.168.123.2/32 0.0.0.0                  0         32768 i
 *>  192.168.123.3/32 10.10.10.1                             0 1 20 i

For address family: VPNv4 Unicast

BGP table version is 3, local router ID is 192.168.123.2
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter,
              x best-external, a additional-path, c RIB-compressed,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 1.1.2.10:10 (default for vrf cust10)
 *>  1.1.2.10/32      0.0.0.0                  0         32768 ?
Route Distinguisher: 1.1.2.20:10 (default for vrf cust20)
 *>  1.1.2.20/32      0.0.0.0                  0         32768 ?

For address family: IPv4 Multicast


For address family: VPNv4 Multicast


For address family: MVPNv4 Unicast
"""
    )
    assert len(records) == 5
    assert records[0] == IosBgpAddressFamily(
        name="IPv4 Unicast",
        router_id="192.168.123.2",
        vrfs=(
            IosBgpVrf(
                name="default",
                route_distinguisher=None,
                routes=(
                    IosBgpRoute(
                        network="10.10.10.0/24",
                        next_hop_ip="10.10.10.1",
                        best_path=True,  # r>
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(1,),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="192.168.122.0/24",
                        next_hop_ip="10.10.10.1",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(1,),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="192.168.123.1/32",
                        next_hop_ip="10.10.10.1",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(1,),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="192.168.123.2/32",
                        next_hop_ip="0.0.0.0",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=32768,
                        as_path=(),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="192.168.123.3/32",
                        next_hop_ip="10.10.10.1",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(1, 20),
                        origin_type="i",
                    ),
                ),
            ),
        ),
    )
    assert records[1] == IosBgpAddressFamily(
        name="VPNv4 Unicast",
        router_id="192.168.123.2",
        vrfs=(
            IosBgpVrf(
                name="cust10",
                route_distinguisher="1.1.2.10:10",
                routes=(
                    IosBgpRoute(
                        network="1.1.2.10/32",
                        next_hop_ip="0.0.0.0",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=32768,
                        as_path=(),
                        origin_type="?",
                    ),
                ),
            ),
            IosBgpVrf(
                name="cust20",
                route_distinguisher="1.1.2.20:10",
                routes=(
                    IosBgpRoute(
                        network="1.1.2.20/32",
                        next_hop_ip="0.0.0.0",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=32768,
                        as_path=(),
                        origin_type="?",
                    ),
                ),
            ),
        ),
    )
    assert records[2] == IosBgpAddressFamily(
        name="IPv4 Multicast", router_id=None, vrfs=()
    )
    assert records[3] == IosBgpAddressFamily(
        name="VPNv4 Multicast", router_id=None, vrfs=()
    )
    assert records[4] == IosBgpAddressFamily(
        name="MVPNv4 Unicast", router_id=None, vrfs=()
    )


def test_local_default_route() -> None:
    # The default route in this show data results from neighbor default-originate.
    # This is a per-neighbor command and Batfish does not install these default
    # routes in its BGP RIB (and they're not valid or best-path anyway).
    records = parse_show_bgp_all(
        """For address family: IPv4 Unicast

BGP table version is 18, local router ID is 2.2.2.2
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter,
              x best-external, a additional-path, c RIB-compressed,
              t secondary path,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
      0.0.0.0          0.0.0.0                                0 i
 *>   1.1.1.1/32       10.10.100.1                            0 65000 i
      1.1.1.2/32       10.10.100.2                            0 65000 i
"""
    )
    assert records[0] == IosBgpAddressFamily(
        name="IPv4 Unicast",
        router_id="2.2.2.2",
        vrfs=(
            IosBgpVrf(
                name="default",
                route_distinguisher=None,
                routes=(
                    IosBgpRoute(
                        network="0.0.0.0/0",
                        next_hop_ip="0.0.0.0",
                        best_path=False,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="1.1.1.1/32",
                        next_hop_ip="10.10.100.1",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(65000,),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="1.1.1.2/32",
                        next_hop_ip="10.10.100.2",
                        best_path=False,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(65000,),
                        origin_type="i",
                    ),
                ),
            ),
        ),
    )


def test_ecmp() -> None:
    records = parse_show_bgp_all(
        """For address family: IPv4 Unicast

BGP table version is 18, local router ID is 2.2.2.2
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter,
              x best-external, a additional-path, c RIB-compressed,
              t secondary path,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   1.1.1.3/32       10.10.100.1                            0 65000 65001 i
 *m                    10.10.101.1                            0 65000 65001 i
 *>   1.1.1.4/32       10.10.101.1                            0 65000 65001 i
 *    1.1.1.5/32       10.10.101.1                            0 65000 65001 i

"""
    )
    assert records[0] == IosBgpAddressFamily(
        name="IPv4 Unicast",
        router_id="2.2.2.2",
        vrfs=(
            IosBgpVrf(
                name="default",
                route_distinguisher=None,
                routes=(
                    IosBgpRoute(
                        network="1.1.1.3/32",
                        next_hop_ip="10.10.100.1",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(65000, 65001),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="1.1.1.3/32",
                        next_hop_ip="10.10.101.1",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(65000, 65001),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="1.1.1.4/32",
                        next_hop_ip="10.10.101.1",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(65000, 65001),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="1.1.1.5/32",
                        next_hop_ip="10.10.101.1",
                        best_path=False,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(65000, 65001),
                        origin_type="i",
                    ),
                ),
            ),
        ),
    )


def test_parse_show_bgp_all_ecmp() -> None:
    """
    Test bgp ecmp routes parsing
    """
    records = parse_show_bgp_all(
        """For address family: IPv4 Unicast

BGP table version is 31, local router ID is 2.2.2.2
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter,
              x best-external, a additional-path, c RIB-compressed,
              t secondary path,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>i  10.1.2.0/24      10.8.1.1                 0    100      0 65000 65001 i
 * i                   10.9.1.2                 0    100      0 65000 65001 i
 * i  10.1.3.0/24      10.8.1.3                 0    100      0 65000 65001 i
 *>i                   10.9.1.4                 0    100      0 65000 65001 i
 * i  10.1.4.0/24      10.8.1.3                 0    100      0 65000 65001 i
 *>                    10.9.1.4                 0    100      0 65000 65001 i
 s>i 2.128.0.0/24     2.34.101.4              50    350      0 65001 i
 s ia                 2.34.201.4              50    350      0 65001 i

"""
    )
    assert records[0] == IosBgpAddressFamily(
        name="IPv4 Unicast",
        router_id="2.2.2.2",
        vrfs=(
            IosBgpVrf(
                name="default",
                route_distinguisher=None,
                routes=(
                    IosBgpRoute(
                        network="10.1.2.0/24",
                        next_hop_ip="10.8.1.1",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(65000, 65001),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="10.1.2.0/24",
                        next_hop_ip="10.9.1.2",
                        best_path=False,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(65000, 65001),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="10.1.3.0/24",
                        next_hop_ip="10.8.1.3",
                        best_path=False,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(65000, 65001),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="10.1.3.0/24",
                        next_hop_ip="10.9.1.4",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(65000, 65001),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="10.1.4.0/24",
                        next_hop_ip="10.8.1.3",
                        best_path=False,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(65000, 65001),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="10.1.4.0/24",
                        next_hop_ip="10.9.1.4",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(65000, 65001),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="2.128.0.0/24",
                        next_hop_ip="2.34.101.4",
                        best_path=True,  # s>i
                        metric=50,
                        local_preference=350,
                        weight=0,
                        as_path=(65001,),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="2.128.0.0/24",
                        next_hop_ip="2.34.201.4",
                        best_path=False,  # s ia
                        metric=50,
                        local_preference=350,
                        weight=0,
                        as_path=(65001,),
                        origin_type="i",
                    ),
                ),
            ),
        ),
    )


def test_parse_show_bgp_all_metric_absent() -> None:
    """
    Test bgp routes parsing when metric value is not present
    """

    input_text = """For address family: IPv4 Unicast

BGP table version is 13, local router ID is 1.10.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter,
              x best-external, a additional-path, c RIB-compressed,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 r>i  0.0.0.0          111.111.111.111               300      0 65100 3356 i
 r>i  1.0.1.0/24       1.1.1.1                       400      0 65100 3356 i
 r>i  1.0.1.0/24       1.1.1.1                  1    500      0 65100 3356 i
"""
    records = parse_show_bgp_all(input_text)
    assert records[0] == IosBgpAddressFamily(
        name="IPv4 Unicast",
        router_id="1.10.1.1",
        vrfs=(
            IosBgpVrf(
                name="default",
                route_distinguisher=None,
                routes=(
                    IosBgpRoute(
                        network="0.0.0.0/0",
                        next_hop_ip="111.111.111.111",
                        best_path=True,  # r>i
                        metric=0,
                        local_preference=300,
                        weight=0,
                        as_path=(65100, 3356),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="1.0.1.0/24",
                        next_hop_ip="1.1.1.1",
                        best_path=True,  # r>i
                        metric=0,
                        local_preference=400,
                        weight=0,
                        as_path=(65100, 3356),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="1.0.1.0/24",
                        next_hop_ip="1.1.1.1",
                        best_path=True,  # r>i
                        metric=1,
                        local_preference=500,
                        weight=0,
                        as_path=(65100, 3356),
                        origin_type="i",
                    ),
                ),
            ),
        ),
    )


def test_parse_show_bgp_all() -> None:
    """
    Test bgp routes parsing
    """

    input_text = """For address family: IPv4 Unicast

BGP table version is 13, local router ID is 1.10.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter,
              x best-external, a additional-path, c RIB-compressed,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 r>i 1.0.1.0/24       1.1.1.1                  0    100      0 i
 * ia2.128.0.0/16     10.13.22.3              50    350      0 3 2 i
 *  a3.0.1.0/24       10.12.11.2              50    350      0 2 3 i
 *m a1.0.1.0/24       2.34.101.3              50    350      0 2 1 i
 r>i 192.168.123.11/32
                       2.1.1.2                  0    100      0 i
"""

    records = parse_show_bgp_all(input_text)
    assert records[0] == IosBgpAddressFamily(
        name="IPv4 Unicast",
        router_id="1.10.1.1",
        vrfs=(
            IosBgpVrf(
                name="default",
                route_distinguisher=None,
                routes=(
                    IosBgpRoute(
                        network="1.0.1.0/24",
                        next_hop_ip="1.1.1.1",
                        best_path=True,  # r>i
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="2.128.0.0/16",
                        next_hop_ip="10.13.22.3",
                        best_path=False,
                        metric=50,
                        local_preference=350,
                        weight=0,
                        as_path=(3, 2),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="3.0.1.0/24",
                        next_hop_ip="10.12.11.2",
                        best_path=False,
                        metric=50,
                        local_preference=350,
                        weight=0,
                        as_path=(2, 3),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="1.0.1.0/24",
                        next_hop_ip="2.34.101.3",
                        best_path=True,
                        metric=50,
                        local_preference=350,
                        weight=0,
                        as_path=(2, 1),
                        origin_type="i",
                    ),
                    IosBgpRoute(
                        network="192.168.123.11/32",
                        next_hop_ip="2.1.1.2",
                        best_path=True,  # r>i
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(),
                        origin_type="i",
                    ),
                ),
            ),
        ),
    )


def test_af_table_routes_vrf() -> None:
    # with router id
    input_text = """
Route Distinguisher: 65003:1 (default for vrf d1_ce) VRF Router ID 192.168.123.31
 *>   10.13.11.0/30    0.0.0.0                  0         32768 ?
    """
    parsed_output = _af_table_routes_vrf().parseString(input_text)

    assert parsed_output[0][0]["rd"] == "65003:1"
    assert parsed_output[0][0]["vrf_name"] == "d1_ce"
    assert parsed_output[0][0]["vrf_router_id"] == "192.168.123.31"

    assert parsed_output[0][1]["status"] == "*>"
    assert parsed_output[0][1]["network"] == "10.13.11.0/30"
    assert parsed_output[0][1]["next_hop"].strip() == "0.0.0.0"
    assert parsed_output[0][1]["metric"].strip() == "0"
    assert not parsed_output[0][1]["local_preference"].strip()
    assert parsed_output[0][1]["weight"] == 32768
    assert parsed_output[0][1]["origin_type"] == "?"

    # without router id
    input_text = """
Route Distinguisher: 65003:1 (default for vrf d1_ce)
 *>   10.13.11.0/30    0.0.0.0                  0         32768 ?
    """
    parsed_output = _af_table_routes_vrf().parseString(input_text)

    assert parsed_output[0][0]["rd"] == "65003:1"
    assert parsed_output[0][0]["vrf_name"] == "d1_ce"

    assert parsed_output[0][1]["status"] == "*>"
    assert parsed_output[0][1]["network"] == "10.13.11.0/30"
    assert parsed_output[0][1]["next_hop"].strip() == "0.0.0.0"
    assert parsed_output[0][1]["metric"].strip() == "0"
    assert not parsed_output[0][1]["local_preference"].strip()
    assert parsed_output[0][1]["weight"] == 32768
    assert parsed_output[0][1]["origin_type"] == "?"


def test_parse_show_bgp_all_vrf_routes_with_router_id() -> None:
    # Test parsing of bgp route in vrf router id set for the vrf
    records = parse_show_bgp_all(
        """For address family: IPv4 Unicast

For address family: IPv6 Unicast


For address family: VPNv4 Unicast

BGP table version is 17, local router ID is 192.168.123.3
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter,
              x best-external, a additional-path, c RIB-compressed,
              t secondary path,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 65003:1 (default for vrf d1_ce) VRF Router ID 192.168.123.31
 *>   10.13.11.0/30    0.0.0.0                  0         32768 ?

For address family: IPv4 Multicast


For address family: VPNv4 Multicast


For address family: MVPNv4 Unicast
"""
    )

    assert len(records) == 6
    assert records[2] == IosBgpAddressFamily(
        name="VPNv4 Unicast",
        router_id="192.168.123.3",
        vrfs=(
            IosBgpVrf(
                name="d1_ce",
                route_distinguisher="65003:1",
                routes=(
                    IosBgpRoute(
                        network="10.13.11.0/30",
                        next_hop_ip="0.0.0.0",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=32768,
                        as_path=(),
                        origin_type="?",
                    ),
                ),
            ),
        ),
    )
