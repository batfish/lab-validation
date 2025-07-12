from lab_validation.parsers.iosxr.commands.show_bgp_all_all import (
    _af_table_routes_vrf_route,
    parse_show_bgp_all_all,
)
from lab_validation.parsers.iosxr.models.bgp import (
    IosXrBgpAddressFamily,
    IosXrBgpRoute,
    IosXrBgpVrf,
)


def test_multi_path_parsing() -> None:
    records = parse_show_bgp_all_all(
        """Address Family: VPNv4 Unicast
-----------------------------

BGP router identifier 10.169.0.21, local AS number 65137
BGP generic scan interval 60 secs
Non-stop routing is enabled
BGP table state: Active
Table ID: 0x0   RD version: 0
BGP main routing table version 35
BGP NSR Initial initsync version 21 (Reached)
BGP NSR/ISSU Sync-Group versions 0/0
BGP scan interval 60 secs

Status codes: s suppressed, d damped, h history, * valid, > best
              i - internal, r RIB-failure, S stale, N Nexthop-discard
Origin codes: i - IGP, e - EGP, ? - incomplete
   Network            Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.169.0.21:90 (default for vrf VRFB)
*> 10.208.1.0/31      0.0.0.0                  0         32768 ?
* i                   10.208.1.1               0    100      0 ?
*> 10.208.1.30/31     0.0.0.0                  0         32768 ?
*> 172.60.0.0/16      0.0.0.0                  0         32768 ?

Processed 3 prefixes, 4 paths

Address Family: IPv4 Unicast
----------------------------
"""
    )
    assert len(records) == 2
    assert records[0] == IosXrBgpAddressFamily(
        name="VPNv4 Unicast",
        router_id="10.169.0.21",
        local_as=65137,
        vrfs=(
            IosXrBgpVrf(
                name="VRFB",
                route_distinguisher="10.169.0.21:90",
                routes=(
                    IosXrBgpRoute(
                        network="10.208.1.0/31",
                        next_hop_ip="0.0.0.0",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=32768,
                        as_path=(),
                        origin_type="?",
                    ),
                    IosXrBgpRoute(
                        network="10.208.1.0/31",
                        next_hop_ip="10.208.1.1",
                        best_path=False,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(),
                        origin_type="?",
                    ),
                    IosXrBgpRoute(
                        network="10.208.1.30/31",
                        next_hop_ip="0.0.0.0",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=32768,
                        as_path=(),
                        origin_type="?",
                    ),
                    IosXrBgpRoute(
                        network="172.60.0.0/16",
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
    assert records[1] == IosXrBgpAddressFamily(
        name="IPv4 Unicast", router_id=None, local_as=None, vrfs=()
    )


def test_parsing() -> None:
    records = parse_show_bgp_all_all(
        """Address Family: VPNv4 Unicast
-----------------------------

BGP router identifier 10.188.62.3, local AS number 65100
BGP generic scan interval 60 secs
Non-stop routing is enabled
BGP table state: Active
Table ID: 0x0   RD version: 0
BGP main routing table version 14
BGP NSR Initial initsync version 5 (Reached)
BGP NSR/ISSU Sync-Group versions 0/0
BGP scan interval 60 secs

Status codes: s suppressed, d damped, h history, * valid, > best
              i - internal, r RIB-failure, S stale, N Nexthop-discard
Origin codes: i - IGP, e - EGP, ? - incomplete
   Network            Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.188.62.3:151 (default for vrf AZURE)
*> 10.77.0.0/17       10.103.127.6            10     20      0 65300 65300 i
*> 10.77.128.0/17     10.103.127.6             0             0 65300 i
*>i192.168.122.0/24   100.103.127.126               100      0 65300 i
*> 192.168.123.2/32   0.0.0.0                  0         32768 ?
s> 128.2.0.0/16       0.0.0.0                  0         32768 i

Processed 4 prefixes, 4 paths

Address Family: IPv4 Unicast
----------------------------

"""
    )
    assert len(records) == 2
    assert records[0] == IosXrBgpAddressFamily(
        name="VPNv4 Unicast",
        router_id="10.188.62.3",
        local_as=65100,
        vrfs=(
            IosXrBgpVrf(
                name="AZURE",
                route_distinguisher="10.188.62.3:151",
                routes=(
                    IosXrBgpRoute(
                        network="10.77.0.0/17",
                        next_hop_ip="10.103.127.6",
                        best_path=True,
                        metric=10,
                        local_preference=20,
                        weight=0,
                        as_path=(
                            65300,
                            65300,
                        ),
                        origin_type="i",
                    ),
                    IosXrBgpRoute(
                        network="10.77.128.0/17",
                        next_hop_ip="10.103.127.6",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=0,
                        as_path=(65300,),
                        origin_type="i",
                    ),
                    IosXrBgpRoute(
                        network="192.168.122.0/24",
                        next_hop_ip="100.103.127.126",
                        best_path=True,
                        metric=None,
                        local_preference=100,
                        weight=0,
                        as_path=(65300,),
                        origin_type="i",
                    ),
                    IosXrBgpRoute(
                        network="192.168.123.2/32",
                        next_hop_ip="0.0.0.0",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=32768,
                        as_path=(),
                        origin_type="?",
                    ),
                    IosXrBgpRoute(
                        network="128.2.0.0/16",
                        next_hop_ip="0.0.0.0",
                        best_path=True,
                        metric=0,
                        local_preference=100,
                        weight=32768,
                        as_path=(),
                        origin_type="i",
                    ),
                ),
            ),
        ),
    )
    assert records[1] == IosXrBgpAddressFamily(
        name="IPv4 Unicast", router_id=None, local_as=None, vrfs=()
    )


def test_parsing_default_vrf() -> None:
    records = parse_show_bgp_all_all(
        """Address Family: IPv4 Unicast
----------------------------

BGP router identifier 10.188.62.3, local AS number 65100
BGP generic scan interval 60 secs
Non-stop routing is enabled
BGP table state: Active
Table ID: 0xe0000000   RD version: 15
BGP main routing table version 15
BGP NSR Initial initsync version 4 (Reached)
BGP NSR/ISSU Sync-Group versions 0/0
BGP scan interval 60 secs

Status codes: s suppressed, d damped, h history, * valid, > best
              i - internal, r RIB-failure, S stale, N Nexthop-discard
Origin codes: i - IGP, e - EGP, ? - incomplete
   Network            Next Hop            Metric LocPrf Weight Path
*> 10.0.0.0/8         0.0.0.0                            32768 i

Processed 1 prefixes, 1 paths
"""
    )
    assert len(records) == 1
    assert records[0] == IosXrBgpAddressFamily(
        name="IPv4 Unicast",
        router_id="10.188.62.3",
        local_as=65100,
        vrfs=(
            IosXrBgpVrf(
                name="default",
                route_distinguisher=None,
                routes=(
                    IosXrBgpRoute(
                        network="10.0.0.0/8",
                        next_hop_ip="0.0.0.0",
                        best_path=True,
                        metric=None,
                        local_preference=100,
                        weight=32768,
                        as_path=(),
                        origin_type="i",
                    ),
                ),
            ),
        ),
    )


def test_6152() -> None:
    """Test parsing of suppressed BGP routes with multiple status codes (e.g. 's i')"""
    record = _af_table_routes_vrf_route().parseString(
        """s i210.171.104.0/24   10.169.6.153                  100      0 65240 i
"""
    )[0]
    assert record.status == "s i"
    assert record.network == "210.171.104.0/24"
    # Rest is tested elsewhere
