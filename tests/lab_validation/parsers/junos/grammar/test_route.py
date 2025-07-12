from lab_validation.parsers.junos.grammar.route import (
    _bgp_route_info_block,
    _direct_route_info_block,
    _isis_route_info_block,
    _local_route_info_block,
    _ospf_route_info_block,
    _route_block,
    _route_info_block,
    _static_discard_route_info_block,
    _static_route_info_block,
    _status_route_info_block,
)


def test_route_block() -> None:
    parsed_data = _route_block().parseString(
        """10.10.50.0/24      *[Direct/0] 01:48:58
                    > via em0.0
                    [BGP/170] 01:48:54, MED 0, localpref 100
                      AS path: 1 I, validation-state: unverified
                    > to 10.10.50.1 via em0.0
        """
    )
    assert (
        parsed_data.network == "10.10.50.0/24"
        and len(parsed_data.info) == 2
        and parsed_data.info[0].protocol == "Direct"
        and parsed_data.info[1].protocol == "BGP"
    )


def test_route_info_block() -> None:
    parsed_data = _route_info_block().parseString(
        """[Direct/0] 01:48:58
            > via em0.0
           [BGP/170] 01:48:54, MED 0, localpref 100
           AS path: 1 10 I, validation-state: unverified
           > to 10.10.50.1 via em0.0
        """
    )
    assert (
        len(parsed_data) == 2
        and parsed_data[0].protocol == "Direct"
        and parsed_data[1].protocol == "BGP"
    )


def test_route_info_block_no_med() -> None:
    parsed_data = _route_info_block().parseString(
        """*[Direct/0] 03:26:32
                > via em3.0
                [BGP/170] 01:08:18, localpref 100
                  AS path: 1 I, validation-state: valid
                > to 10.45.33.1 via em3.0
        """
    )
    assert (
        len(parsed_data) == 2
        and parsed_data[0].protocol == "Direct"
        and parsed_data[1].protocol == "BGP"
    )


def test_status_route_info_block() -> None:
    parsed_data = _status_route_info_block().parseString(
        """*[Direct/0] 01:48:58
            > via em0.0
        """
    )
    assert parsed_data.status == "*"

    parsed_data = _status_route_info_block().parseString(
        """+[Direct/0] 01:48:58
            > via em0.0
        """
    )
    assert parsed_data.status == "+"

    parsed_data = _status_route_info_block().parseString(
        """-[Direct/0] 01:48:58
            > via em0.0
        """
    )
    assert parsed_data.status == "-"

    parsed_data = _status_route_info_block().parseString(
        """[Direct/0] 01:48:58
            > via em0.0
        """
    )
    assert parsed_data.status == ""


def test_local_route_info() -> None:
    parsed_data = _local_route_info_block().parseString(
        """[Local/0] 02:05:54
                      Local via em1.0
        """
    )
    assert (
        parsed_data.protocol == "Local"
        and parsed_data.admin == 0
        and parsed_data.nh_iface == "em1.0"
    )


def test_direct_route_info() -> None:
    """Test if we can parse the direct route info block"""
    parsed_data = _direct_route_info_block().parseString(
        """[Direct/0] 01:48:58
            > via em0.0
        """
    )
    assert (
        parsed_data.protocol == "Direct"
        and parsed_data.admin == 0
        and parsed_data.nh_iface == "em0.0"
    )


def test_static_discard_route_info() -> None:
    """Test if we can parse the static discard route info block"""
    parsed_data = _static_discard_route_info_block().parseString(
        """[Static/5] 00:08:11
        Discard
        """
    )
    assert parsed_data.protocol == "Static" and parsed_data.admin == 5


def test_static_route_info() -> None:
    """Test if we can parse the static route info block"""
    parsed_data = _static_route_info_block().parseString(
        """[Static/5] 00:07:57
        > to 10.46.55.2 via em5.0
        """
    )
    assert (
        parsed_data.protocol == "Static"
        and parsed_data.admin == 5
        and parsed_data.nh_ip == "10.46.55.2"
        and parsed_data.nh_iface == "em5.0"
    )


def test_isis_route_info() -> None:
    """Test if we can parse the is-is route info block"""
    parsed_data = _isis_route_info_block().parseString(
        """[IS-IS/15] 00:07:47, metric 10
        > to 10.34.11.1 via em1.0
        """
    )
    assert (
        parsed_data.protocol == "IS-IS"
        and parsed_data.admin == 15
        and parsed_data.metric == 10
        and parsed_data.nh_ip == "10.34.11.1"
        and parsed_data.nh_iface == "em1.0"
    )


def test_bgp_route_info() -> None:
    """Test if we can parse the bgp route info block"""
    parsed_data = _bgp_route_info_block().parseString(
        """[BGP/170] 01:48:54, MED 0, localpref 100
        AS path: 1 10 I, validation-state: unverified
        > to 10.10.50.1 via em0.0
        """
    )
    assert (
        parsed_data.protocol == "BGP"
        and parsed_data.admin == 170
        and parsed_data.metric == 0
        and parsed_data.localpref == 100
        and len(parsed_data.as_path) == 2
        and parsed_data.as_path[0].as_numbers == 1
        and parsed_data.as_path[1].as_numbers == 10
        and parsed_data.nh_ip == "10.10.50.1"
        and parsed_data.nh_iface == "em0.0"
    )


def test_bgp_route_info_no_as_path() -> None:
    """Test if we can parse the bgp route info where as path is empty"""
    parsed_data = _bgp_route_info_block().parseString(
        """[BGP/170] 04:14:18, localpref 100
                  AS path: I, validation-state: valid
                > to 10.12.11.1 via em1.0
        """
    )
    assert parsed_data.protocol == "BGP"
    assert parsed_data.admin == 170
    assert parsed_data.metric == ""
    assert parsed_data.localpref == 100
    assert list(parsed_data.as_path) == []
    assert parsed_data.origin_type == "I"
    assert parsed_data.nh_ip == "10.12.11.1"
    assert parsed_data.nh_iface == "em1.0"


def test_ospf_route_info() -> None:
    parsed_data = _ospf_route_info_block().parseString(
        """
        [OSPF/10] 02:12:38, metric 2
                    > to 10.16.63.2 via em1.0
        """
    )
    assert parsed_data.protocol == "OSPF"
    assert parsed_data.admin == 10
    assert parsed_data.metric == 2
    assert parsed_data.nh_ip == "10.16.63.2"
    assert parsed_data.nh_iface == "em1.0"
