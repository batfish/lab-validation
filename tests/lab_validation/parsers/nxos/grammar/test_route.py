import pytest
from pyparsing import ParseException

from lab_validation.parsers.nxos.grammar.route import (
    _next_hop_line,
    _null_routed_line,
    _prefix_line,
    _protocol,
    _uptime,
    _v4_route_for_a_prefix,
    show_route,
)


def test_show_route() -> None:
    records = show_route().parseString(
        """
        IP Route Table for VRF "default"
            '*' denotes best ucast next-hop
            '**' denotes best mcast next-hop
            '[x/y]' denotes [preference/metric]
            '%<string>' in via output denotes VRF <string>

            1.1.1.1/32, ubest/mbest: 1/0
                *via 10.10.11.1, [200/0], 03:27:56, bgp-65001, internal, tag 65001
            1.1.1.3/32, ubest/mbest: 2/0, attached
                *via 1.1.1.3, Lo0, [0/0], 03:23:20, local
                *via 1.1.1.3, Lo0, [0/0], 03:23:20, direct
        """
    )
    assert records.vrf == "default"
    assert len(records.v4_routes) == 2


def test_v4_route_for_a_prefix() -> None:
    result = _v4_route_for_a_prefix().parseString(
        """
        2.2.2.2/32, ubest/mbest: 2/0, attached
        *via 2.2.2.2, Lo0, [0/10], 01:05:49, local
        *via 2.2.2.3, Lo1, [1/2], 01:05:49, direct
        """
    )
    assert result.network == "2.2.2.2/32"
    assert len(result.next_hops) == 2
    nh = result.next_hops[0]
    assert nh.nhip == "2.2.2.2"
    assert nh.nhint == "Lo0"
    assert nh.admin == 0
    assert nh.metric == 10
    assert nh.local == "local"
    nh = result.next_hops[1]
    assert nh.nhip == "2.2.2.3"
    assert nh.nhint == "Lo1"
    assert nh.admin == 1
    assert nh.metric == 2
    assert nh.direct == "direct"


def test_prefix_line() -> None:
    result = _prefix_line().parseString(
        """
        2.2.2.2/32, ubest/mbest: 2/0, attached
        """
    )
    assert result.network == "2.2.2.2/32"


def test_null_routed_line() -> None:
    result = _null_routed_line().parseString(
        """
        *via Null0, [220/0], 03:28:31, bgp-65114, discard, tag 65114
        """
    )
    assert "nhip" not in result
    assert result.nhint == "Null0"
    assert result.admin == 220
    assert result.metric == 0
    assert result.bgp
    assert result.process == "bgp-65114"
    assert result.tag == 65114


def test_ebgp_next_hop_line() -> None:
    result = _next_hop_line().parseString(
        """
        *via 10.10.100.1, [20/0], 01:03:27, bgp-65100, external, tag 65000
        """
    )
    assert result.nhip == "10.10.100.1"
    assert result.admin == 20
    assert result.metric == 0
    assert result.bgp
    assert result.process == "bgp-65100"
    assert result.extension == "external"
    assert result.tag == 65000


def test_ibgp_next_hop_line() -> None:
    result = _next_hop_line().parseString(
        """
        *via 10.10.11.1, [200/0], 03:27:40, bgp-65001, internal, tag 65001
        """
    )
    assert result.nhip == "10.10.11.1"
    assert result.admin == 200
    assert result.metric == 0
    assert result.bgp
    assert result.process == "bgp-65001"
    assert result.extension == "internal"
    assert result.tag == 65001


def test_eigrp_next_hop_line() -> None:
    result = _next_hop_line().parseString(
        """
        *via 10.13.21.1, Eth1/1, [170/2585856], 01:32:31, eigrp-1, external
        """
    )
    assert result.nhip == "10.13.21.1"
    assert result.admin == 170
    assert result.metric == 2585856
    assert result.eigrp
    assert result.process == "eigrp-1"
    assert result.extension == "external"


def test_eigrp_external_next_hop_line() -> None:
    result = _next_hop_line().parseString(
        """
        *via 10.13.21.2, Eth1/2, [90/130816], 01:32:30, eigrp-1, internal
        """
    )
    assert result.nhip == "10.13.21.2"
    assert not result.nhvrf
    assert result.admin == 90
    assert result.metric == 130816
    assert result.eigrp
    assert result.process == "eigrp-1"
    assert result.extension == "internal"
    assert not result.evpn
    assert not result.vxlan


def test_evpn_next_hop_line() -> None:
    result = _next_hop_line().parseString(
        """
        *via 2.2.2.2%default, [200/0], 02:35:20, bgp-65001, internal, tag 65200 (evpn) segid: 100333 tunnelid: 0x2020202 encap: VXLAN
        """
    )
    assert result.nhip == "2.2.2.2"
    assert result.nhvrf == "default"
    assert result.admin == 200
    assert result.metric == 0
    assert result.bgp
    assert result.process == "bgp-65001"
    assert result.extension == "internal"
    assert result.tag == 65200
    assert result.evpn
    assert result.vxlan
    assert result.segid == 100333
    assert result.tunnelid == "2020202"


def test_vxlan_static_next_hop_line() -> None:
    result = _next_hop_line().parseString(
        """
        *via 10.198.226.133, [1/0], 22w6d, static, tag 65333 segid: 3002 tunnelid: 0xac6e045 encap: VXLAN
        """
    )
    assert result.nhip == "10.198.226.133"
    assert not result.nhvrf
    assert result.admin == 1
    assert result.metric == 0
    assert result.static
    assert result.tag == 65333
    assert not result.evpn
    assert result.vxlan
    assert result.segid == 3002
    assert result.tunnelid == "ac6e045"


def test_direct_next_hop_line() -> None:
    result = _next_hop_line().parseString(
        """
        *via 192.168.10.1, Vlan10, [0/0], 03:31:02, direct
        """
    )
    assert result.nhip == "192.168.10.1"
    assert result.nhint == "Vlan10"
    assert result.admin == 0
    assert result.metric == 0
    assert result.direct == "direct"


def test_hsrp_next_hop_line() -> None:
    result = _next_hop_line().parseString(
        """
        *via 10.102.5.35, Vlan101, [0/0], 49w3d, hsrp
        """
    )
    assert result.nhip == "10.102.5.35"
    assert result.nhint == "Vlan101"
    assert result.admin == 0
    assert result.metric == 0
    assert result.hsrp == "hsrp"


def test_uptime() -> None:
    # valid ones don't raise
    _uptime().parseString("01:05:49")
    _uptime().parseString("2d02h")
    _uptime().parseString("30w4d")
    _uptime().parseString("2y12w")
    _uptime().parseString("0.000000")
    # validate that invalid ones will
    with pytest.raises(ParseException):
        _uptime().parseString("not-a-time")


def test_local_next_hop_line() -> None:
    result = _next_hop_line().parseString(
        """
        *via 2.2.2.2, Lo0, [0/0], 01:05:49, local
        """
    )
    assert result.nhip == "2.2.2.2"
    assert result.nhint == "Lo0"
    assert result.admin == 0
    assert result.metric == 0
    assert result.local == "local"


def test_ospf_next_hop_line_type5() -> None:
    result = _next_hop_line().parseString(
        """
        *via 15.1.1.1, Eth1/1, [110/41], 00:26:29, ospf-5, inter
        """
    )
    assert result.nhip == "15.1.1.1"
    assert result.nhint == "Eth1/1"
    assert result.admin == 110
    assert result.metric == 41
    assert result.ospf
    assert result.process == "ospf-5"


def test_static_next_hop_line() -> None:
    result = _next_hop_line().parseString(
        """
        *via 10.12.11.2, [1/0], 03:16:08, static
        """
    )
    assert result.nhip == "10.12.11.2"
    assert result.admin == 1
    assert result.metric == 0
    assert result.static == "static"


def test_next_hop_line_subinterface() -> None:
    result = _next_hop_line().parseString(
        """
        *via 10.10.100.1, Eth1/2.313, [0/0], 23:53:40, direct
        """
    )
    assert result.nhip == "10.10.100.1"
    assert result.nhint == "Eth1/2.313"
    assert result.admin == 0
    assert result.metric == 0
    assert result.direct == "direct"


def test_protocol() -> None:
    # valid ones don't raise
    _protocol().parseString("am")
    _protocol().parseString("bgp-11111")
    _protocol().parseString("eigrp-11111, internal")
    _protocol().parseString("direct")
    _protocol().parseString("hmm")
    _protocol().parseString("hsrp")
    _protocol().parseString("local")
    _protocol().parseString("ospf-11111, inter")
    _protocol().parseString("static")
    # validate that invalid ones will barf
    with pytest.raises(ParseException):
        _uptime().parseString("not-a-protocol")


def test_trailing_comma_next_hop_line() -> None:
    result = _next_hop_line().parseString(
        """
        *via 10.10.100.1, [20/0], 01:03:27, bgp-65100, external, tag 65000,
        """
    )
    assert result.nhip == "10.10.100.1"
    assert result.admin == 20
    assert result.metric == 0
    assert result.bgp
    assert result.process == "bgp-65100"
    assert result.extension == "external"
    assert result.tag == 65000


def test_trailing_comma_null_routed_line() -> None:
    result = _null_routed_line().parseString(
        """
        *via Null0, [220/0], 03:28:31, bgp-65114, discard, tag 65114,
        """
    )
    assert "nhip" not in result
    assert result.nhint == "Null0"
    assert result.admin == 220
    assert result.metric == 0
    assert result.bgp
    assert result.process == "bgp-65114"
    assert result.tag == 65114


def test_best_status() -> None:
    result = _next_hop_line().parseString(
        """
        *via 10.198.226.165, [1/0], 28w1d, static, tag 65333 segid: 3002 tunnelid: 0xac6e048 encap: VXLAN
        """
    )
    assert result.best_ucast == "*via"

    result = _next_hop_line().parseString(
        """
        via 10.198.224.94%default, [20/0], 1y32w, bgp-65333, external, tag 65011 (evpn) segid: 3002 tunnelid: 0xac6e05e encap: VXLAN
        """
    )
    assert result.not_best == "via"

    # unlike the previous two lines, this line is not from real data
    result = _next_hop_line().parseString(
        """
        **via 10.198.224.94%default, [20/0], 1y32w, bgp-65333, external, tag 65011 (evpn) segid: 3002 tunnelid: 0xac6e05e encap: VXLAN
        """
    )
    assert result.best_mcast == "**via"
