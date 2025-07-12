import textwrap

import pytest

from lab_validation.parsers.a10.commands.bgp import parse_show_ip_bgp
from lab_validation.parsers.a10.models.bgp import A10BgpRoute
from lab_validation.parsers.common.exceptions import UnrecognizedLinesError


def test_parse_show_ip_bgp() -> None:
    text = textwrap.dedent(
        """\
    BGP Address Family IPv4 Unicast
    BGP table version is 1, local router ID is 10.0.1.2
    Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, l - labeled
                  S Stale, m multipath
    Origin codes: i - IGP, e - EGP, ? - incomplete

       Network          Next Hop             Metric LocPrf Weight Type     Path
    *> 0.0.0.0/0        10.139.1.133              0             0          65333 i
    *> 10.0.0.0/24      0.0.0.0                   0         32768          ?
    *> 10.0.1.1/32      0.0.0.0                   0         32768 FLOATING ?
    *> 10.0.1.2/32      0.0.0.0                   0         32768 VIP      ?
    *> 111.111.111.11/32
                        0.0.0.0                   0         32768 VIP FLAGG?
    *> 10.0.1.4/32      0.0.0.0                   0         32768 NAT      ?

    Total number of prefixes 5
    """
    )
    routes = parse_show_ip_bgp(text)
    assert routes == [
        A10BgpRoute(
            valid=True,
            best=True,
            network="0.0.0.0/0",
            next_hop_ip="10.139.1.133",
            metric=0,
            local_preference=None,
            weight=0,
            type=None,
            as_path=tuple([65333]),
            origin_type="i",
        ),
        A10BgpRoute(
            valid=True,
            best=True,
            network="10.0.0.0/24",
            next_hop_ip="0.0.0.0",
            metric=0,
            local_preference=None,
            weight=32768,
            type=None,
            as_path=tuple([]),
            origin_type="?",
        ),
        A10BgpRoute(
            valid=True,
            best=True,
            network="10.0.1.1/32",
            next_hop_ip="0.0.0.0",
            metric=0,
            local_preference=None,
            weight=32768,
            type="FLOATING",
            as_path=tuple([]),
            origin_type="?",
        ),
        A10BgpRoute(
            valid=True,
            best=True,
            network="10.0.1.2/32",
            next_hop_ip="0.0.0.0",
            metric=0,
            local_preference=None,
            weight=32768,
            type="VIP",
            as_path=tuple([]),
            origin_type="?",
        ),
        A10BgpRoute(
            valid=True,
            best=True,
            network="111.111.111.11/32",
            next_hop_ip="0.0.0.0",
            metric=0,
            local_preference=None,
            weight=32768,
            type="VIP FLAGG",
            as_path=tuple([]),
            origin_type="?",
        ),
        A10BgpRoute(
            valid=True,
            best=True,
            network="10.0.1.4/32",
            next_hop_ip="0.0.0.0",
            metric=0,
            local_preference=None,
            weight=32768,
            type="NAT",
            as_path=tuple([]),
            origin_type="?",
        ),
    ]


def test_unrecognized_line() -> None:
    """Test that parser catches unrecognized lines rather than stop early and silently."""
    text = textwrap.dedent(
        """\
    BGP Address Family IPv4 Unicast
    BGP table version is 1, local router ID is 10.0.1.2
    Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, l - labeled
                  S Stale, m multipath
    Origin codes: i - IGP, e - EGP, ? - incomplete

       Network          Next Hop             Metric LocPrf Weight Type     Path
    *> 0.0.0.0/0        10.139.1.133              0             0          65333 i
    X> 10.0.1.4/32      0.0.0.0                   0         32768 NAT      ?

    Total number of prefixes 5
    """
    )
    with pytest.raises(UnrecognizedLinesError):
        parse_show_ip_bgp(text)
