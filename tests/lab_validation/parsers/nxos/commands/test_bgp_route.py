from collections.abc import Sequence

import pytest
from pyparsing import ParseException

from lab_validation.parsers.common.exceptions import UnrecognizedLinesError
from lab_validation.parsers.nxos.commands.bgp_route import parse_show_ip_bgp_all
from lab_validation.parsers.nxos.models.routes import NxosBgpRoute

_DEFAULT_TABLE_HEADER = """BGP routing table information for VRF default, address family IPv4 Unicast
BGP table version is 20, Local Router ID is 192.168.123.3
Status: s-suppressed, x-deleted, S-stale, d-dampened, h-history, *-valid, >-best
Path type: i-internal, e-external, c-confed, l-local, a-aggregate, r-redist, I-injected
Origin codes: i - IGP, e - EGP, ? - incomplete, | - multipath, & - backup, 2 - best2

   Network            Next Hop            Metric     LocPrf     Weight Path
"""


def test_parse_bgp_route_missing_metric_loc_pref() -> None:
    """Test that we can parse a BGP route which is missing metric and local preference"""
    records: Sequence[NxosBgpRoute] = parse_show_ip_bgp_all(
        _DEFAULT_TABLE_HEADER
        + """*>e192.168.61.2/32    10.10.20.1                                     8 1 10 i
"""
    )
    assert records == [
        NxosBgpRoute(
            network="192.168.61.2/32",
            protocol="bgp",
            next_hop_ip="10.10.20.1",
            metric=0,
            local_preference=100,
            best_path=True,
            weight=8,
            vrf="default",
            as_path=(1, 10),
            origin_type="i",
        )
    ]


def test_parse_bgp_route_missing_metric() -> None:
    """Test that we can parse a BGP route which is missing metric"""
    records = parse_show_ip_bgp_all(
        _DEFAULT_TABLE_HEADER
        + """*>i192.168.61.3/32    0.0.0.0                           100          32768 i
"""
    )
    assert records == [
        NxosBgpRoute(
            network="192.168.61.3/32",
            protocol="ibgp",
            next_hop_ip="0.0.0.0",
            metric=0,
            local_preference=100,
            best_path=True,
            weight=32768,
            vrf="default",
            as_path=(),
            origin_type="i",
        )
    ]


def test_parse_bgp_route_missing_local_pref() -> None:
    """Test that we can parse a BGP route which is missing local preference"""
    input_text = (
        _DEFAULT_TABLE_HEADER
        + """*>e192.168.61.5/32    10.10.20.1               2                     6 1 40 i
"""
    )
    records = parse_show_ip_bgp_all(input_text)
    assert records == [
        NxosBgpRoute(
            network="192.168.61.5/32",
            protocol="bgp",
            next_hop_ip="10.10.20.1",
            metric=2,
            local_preference=100,
            best_path=True,
            weight=6,
            vrf="default",
            as_path=(1, 40),
            origin_type="i",
        )
    ]


def test_parse_bgp_route_least_cost() -> None:
    """Test that we can parse a BGP least-cost(not valid best) route"""
    input_text = (
        _DEFAULT_TABLE_HEADER
        + """* e192.168.123.2/32   10.12.77.2                                     0 65002 i
"""
    )
    records = parse_show_ip_bgp_all(input_text)
    assert records == [
        NxosBgpRoute(
            network="192.168.123.2/32",
            protocol="bgp",
            next_hop_ip="10.12.77.2",
            metric=0,
            local_preference=100,
            best_path=False,
            weight=0,
            vrf="default",
            as_path=(65002,),
            origin_type="i",
        )
    ]


def test_parse_bgp_route_invalid() -> None:
    """Test parsing BGP routes that start with double spaces to prevent regression."""
    input_text = (
        _DEFAULT_TABLE_HEADER
        + """  l114.203.98.0/24    0.0.0.0                           100      32768 i
"""
    )
    records = parse_show_ip_bgp_all(input_text)
    assert records == [
        NxosBgpRoute(
            network="114.203.98.0/24",
            protocol="bgp",
            next_hop_ip="0.0.0.0",
            metric=0,
            local_preference=100,
            best_path=False,
            weight=32768,
            vrf="default",
            as_path=(),
            origin_type="i",
        ),
    ]


def test_parse_bgp_route_all_present() -> None:
    """Test that we can parse a BGP route which is not missing anything"""
    input_text = (
        _DEFAULT_TABLE_HEADER
        + """*>l192.168.61.3/32    0.0.0.0                  1        100      32768 1 2 i
"""
    )
    records = parse_show_ip_bgp_all(input_text)
    assert records == [
        NxosBgpRoute(
            network="192.168.61.3/32",
            protocol="bgp",
            next_hop_ip="0.0.0.0",
            metric=1,
            local_preference=100,
            best_path=True,
            weight=32768,
            vrf="default",
            as_path=(1, 2),
            origin_type="i",
        )
    ]


def test_parser_routes_invalid(caplog) -> None:
    """Test that we catch a crash on invalid text"""
    with pytest.raises(ParseException) as _:
        parse_show_ip_bgp_all("rubbish")


def test_parser_routes_padding(caplog) -> None:
    """UnrecognizedLinesError when the start of the file is valid, but some route has an unsupported status code."""
    with pytest.raises(UnrecognizedLinesError) as _:
        # X is not a valid status code
        parse_show_ip_bgp_all(
            """BGP routing table information for VRF default, address family IPv4 Unicast
BGP table version is 20, Local Router ID is 192.168.123.3
Status: s-suppressed, x-deleted, S-stale, d-dampened, h-history, *-valid, >-best
Path type: i-internal, e-external, c-confed, l-local, a-aggregate, r-redist, I-injected
Origin codes: i - IGP, e - EGP, ? - incomplete, | - multipath, & - backup, 2 - best2

   Network            Next Hop            Metric     LocPrf     Weight Path
*>i10.188.249.196/30  10.188.249.198           0        100          0 ?
*>X10.188.249.196/30  10.188.249.198           0        100          0 ?
"""
        )


def test_parse_bgp_statuses() -> None:
    input_text = """BGP routing table information for VRF default, address family IPv4 Unicast
BGP table version is 20, Local Router ID is 192.168.123.3
Status: s-suppressed, x-deleted, S-stale, d-dampened, h-history, *-valid, >-best
Path type: i-internal, e-external, c-confed, l-local, a-aggregate, r-redist, I-injected
Origin codes: i - IGP, e - EGP, ? - incomplete, | - multipath, & - backup, 2 - best2

   Network            Next Hop            Metric     LocPrf     Weight Path
*>i10.188.249.196/30  10.188.249.198           0        100          0 ?
*|i10.188.249.196/30  10.188.249.198           0        100          0 ?
s r10.188.249.196/30  10.188.249.198           0        100          0 ?
  a10.188.249.196/30  10.188.249.198           0        100          0 ?
  l10.188.249.196/30  10.188.249.198           0        100          0 ?
  e10.188.249.196/30  10.188.249.198           0        100          0 ?
    """
    records = parse_show_ip_bgp_all(input_text)
    assert len(records) == 6
    for i in range(len(records)):
        assert records[i].best_path == (i < 2)


def test_parse_bgp_route_multi_route() -> None:
    input_text = """BGP routing table information for VRF default, address family IPv4 Unicast
BGP table version is 20, Local Router ID is 192.168.123.1
Status: s-suppressed, x-deleted, S-stale, d-dampened, h-history, *-valid, >-best
Path type: i-internal, e-external, c-confed, l-local, a-aggregate, r-redist, I-injected
Origin codes: i - IGP, e - EGP, ? - incomplete, | - multipath, & - backup, 2 - best2

   Network            Next Hop            Metric     LocPrf     Weight Path
* e192.168.123.2/32   10.12.77.2                                     0 65002 i
*>e                   10.12.11.2                                     0 65002 i
* e                   10.12.44.2                                     0 65002 i
    """
    records = parse_show_ip_bgp_all(input_text)
    assert records == [
        NxosBgpRoute(
            network="192.168.123.2/32",
            protocol="bgp",
            next_hop_ip="10.12.77.2",
            metric=0,
            local_preference=100,
            best_path=False,
            weight=0,
            vrf="default",
            as_path=(65002,),
            origin_type="i",
        ),
        NxosBgpRoute(
            network="192.168.123.2/32",
            protocol="bgp",
            next_hop_ip="10.12.11.2",
            metric=0,
            local_preference=100,
            best_path=True,
            weight=0,
            vrf="default",
            as_path=(65002,),
            origin_type="i",
        ),
        NxosBgpRoute(
            network="192.168.123.2/32",
            protocol="bgp",
            next_hop_ip="10.12.44.2",
            metric=0,
            local_preference=100,
            best_path=False,
            weight=0,
            vrf="default",
            as_path=(65002,),
            origin_type="i",
        ),
    ]


def test_parse_multi_vrf() -> None:
    """Test parsing routes in multiple vrfs."""
    input_text = """BGP routing table information for VRF cust20, address family IPv4 Unicast
BGP table version is 3, Local Router ID is 1.1.3.20
Status: s-suppressed, x-deleted, S-stale, d-dampened, h-history, *-valid, >-best
Path type: i-internal, e-external, c-confed, l-local, a-aggregate, r-redist, I-injected
Origin codes: i - IGP, e - EGP, ? - incomplete, | - multipath, & - backup, 2 - best2

   Network            Next Hop            Metric     LocPrf     Weight Path
*>r1.1.3.20/32        0.0.0.0                  0        100      32768 ?

BGP routing table information for VRF default, address family IPv4 Unicast
BGP table version is 70, Local Router ID is 192.168.123.3
Status: s-suppressed, x-deleted, S-stale, d-dampened, h-history, *-valid, >-best
Path type: i-internal, e-external, c-confed, l-local, a-aggregate, r-redist, I-injected
Origin codes: i - IGP, e - EGP, ? - incomplete, | - multipath, & - backup, 2 - best2

   Network            Next Hop            Metric     LocPrf     Weight Path
*>e10.10.10.0/24      10.10.20.1               0                     0 1 i
    """
    records = parse_show_ip_bgp_all(input_text)
    assert records == [
        NxosBgpRoute(
            network="1.1.3.20/32",
            protocol="bgp",
            next_hop_ip="0.0.0.0",
            metric=0,
            local_preference=100,
            best_path=True,
            weight=32768,
            vrf="cust20",
            as_path=(),
            origin_type="?",
        ),
        NxosBgpRoute(
            network="10.10.10.0/24",
            protocol="bgp",
            next_hop_ip="10.10.20.1",
            metric=0,
            local_preference=100,
            best_path=True,
            weight=0,
            vrf="default",
            as_path=(1,),
            origin_type="i",
        ),
    ]
