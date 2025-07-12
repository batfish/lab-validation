from lab_validation.parsers.junos.grammar.bgp_route import (
    _bgp_route,
    _bgp_route_line2,
    _route_block,
    _table_schema,
    show_bgp_route,
)


def test_show_bgp_route() -> None:
    parsed_data = show_bgp_route().parseString(
        """
        inet.0: 13 destinations, 14 routes (13 active, 0 holddown, 0 hidden)
    + = Active Route, - = Last Active, * = Both

    A V Destination        P Prf   Metric 1   Metric 2  Next hop        AS path
    * V 10.23.33.0/24      B 170        100                             I
      valid                                            >10.12.11.2

    inet6.0: 2 destinations, 2 routes (2 active, 0 holddown, 0 hidden)

    {master:0}
        """
    )
    # empty ribs will be ignored
    assert len(parsed_data) == 1
    rib1 = parsed_data[0]
    assert rib1.vrf_ip_info == "inet.0"
    assert len(rib1.routes) == 1
    route = rib1.routes[0]
    assert route.status == "*"
    assert route.network == "10.23.33.0/24"
    assert route.learn_from == "B"
    assert route.pref == 170
    assert route.metric_1 == 100
    assert route.metric_2 == ""
    assert len(route.as_path) == 0
    assert route.origin_type == "I"
    assert route.is_valid == "valid"
    assert route.is_selected == ">"
    assert route.next_hop == "10.12.11.2"


def test_route_block() -> None:
    parsed_data = _route_block().parseString(
        """
    A V Destination        P Prf   Metric 1   Metric 2  Next hop        AS path
      V 10.12.11.0/24      B 170        100                             I
      valid                                            >10.12.11.2
    * V 192.168.123.5/32   L 120        100                             (65001) 2 I
      valid                                            >10.12.11.2
        """
    )
    assert len(parsed_data.routes) == 2
    route = parsed_data.routes[0]
    assert route.status == ""
    assert route.network == "10.12.11.0/24"
    assert route.learn_from == "B"
    assert route.pref == 170
    assert route.metric_1 == 100
    assert route.metric_2 == ""
    assert len(route.as_path) == 0
    assert route.origin_type == "I"
    assert route.is_valid == "valid"
    assert route.is_selected == ">"
    assert route.next_hop == "10.12.11.2"

    route = parsed_data.routes[1]
    assert route.status == "*"
    assert route.network == "192.168.123.5/32"
    assert route.learn_from == "L"
    assert route.pref == 120
    assert route.metric_1 == 100
    assert route.metric_2 == ""
    assert len(route.as_path) == 2
    assert list(route.as_path[0].as_numbers) == [65001]
    assert route.as_path[1].as_numbers == 2
    assert route.origin_type == "I"
    assert route.is_valid == "valid"
    assert route.is_selected == ">"
    assert route.next_hop == "10.12.11.2"


def test_table_schema() -> None:
    _table_schema().parseString(
        """
        A V Destination        P Prf   Metric 1   Metric 2  Next hop        AS path
        """
    )


def test_bgp_route_not_active() -> None:
    parsed_data = _bgp_route().parseString(
        """
          V 10.12.11.0/24      B 170        100                             I
  valid                                            >10.12.11.2
  """
    )
    assert parsed_data.status == ""
    assert parsed_data.network == "10.12.11.0/24"
    assert parsed_data.learn_from == "B"
    assert parsed_data.pref == 170
    assert parsed_data.metric_1 == 100
    assert parsed_data.metric_2 == ""
    assert len(parsed_data.as_path) == 0
    assert parsed_data.origin_type == "I"
    assert parsed_data.is_valid == "valid"
    assert parsed_data.is_selected == ">"
    assert parsed_data.next_hop == "10.12.11.2"


def test_bgp_route_not_valid() -> None:
    parsed_data = _bgp_route().parseString(
        """
          ? 10.12.11.0/24      B 170        100                             I
  unverified                                            >10.12.11.2
  """
    )
    assert parsed_data.status == ""
    assert parsed_data.network == "10.12.11.0/24"
    assert parsed_data.learn_from == "B"
    assert parsed_data.pref == 170
    assert parsed_data.metric_1 == 100
    assert parsed_data.metric_2 == ""
    assert len(parsed_data.as_path) == 0
    assert parsed_data.origin_type == "I"
    assert parsed_data.is_valid == "unverified"
    assert parsed_data.is_selected == ">"
    assert parsed_data.next_hop == "10.12.11.2"


def test_bgp_route_metric2() -> None:
    parsed_data = _bgp_route().parseString(
        """
          V 10.12.11.0/24      B 170        100    101                         I
  valid                                            >10.12.11.2
  """
    )
    assert parsed_data.status == ""
    assert parsed_data.network == "10.12.11.0/24"
    assert parsed_data.learn_from == "B"
    assert parsed_data.pref == 170
    assert parsed_data.metric_1 == 100
    assert parsed_data.metric_2 == 101
    assert len(parsed_data.as_path) == 0
    assert parsed_data.origin_type == "I"
    assert parsed_data.is_valid == "valid"
    assert parsed_data.is_selected == ">"
    assert parsed_data.next_hop == "10.12.11.2"


def test_bgp_route_active_no_as_path() -> None:
    parsed_data = _bgp_route().parseString(
        """
* V 10.23.33.0/24      B 170        100                             I
  valid                                            >10.12.11.2
  """
    )
    assert parsed_data.status == "*"
    assert parsed_data.network == "10.23.33.0/24"
    assert parsed_data.learn_from == "B"
    assert parsed_data.pref == 170
    assert parsed_data.metric_1 == 100
    assert parsed_data.metric_2 == ""
    assert len(parsed_data.as_path) == 0
    assert parsed_data.origin_type == "I"
    assert parsed_data.is_valid == "valid"
    assert parsed_data.is_selected == ">"
    assert parsed_data.next_hop == "10.12.11.2"


def test_bgp_route_active_with_as_path() -> None:
    parsed_data = _bgp_route().parseString(
        """
* V 10.34.11.0/24      B 170        100                             (65001 65002) 2 I
  valid                                            >10.12.11.2
        """
    )
    assert parsed_data.status == "*"
    assert parsed_data.network == "10.34.11.0/24"
    assert parsed_data.learn_from == "B"
    assert parsed_data.pref == 170
    assert parsed_data.metric_1 == 100
    assert parsed_data.metric_2 == ""
    assert len(parsed_data.as_path) == 2
    assert list(parsed_data.as_path[0].as_numbers) == [65001, 65002]
    assert parsed_data.as_path[1].as_numbers == 2
    assert parsed_data.origin_type == "I"
    assert parsed_data.is_valid == "valid"
    assert parsed_data.is_selected == ">"
    assert parsed_data.next_hop == "10.12.11.2"


def test_bgp_route_line2_unverified() -> None:
    parsed_data = _bgp_route_line2().parseString(
        """
  unverified                                            >10.12.11.2
        """
    )
    assert parsed_data.is_valid == "unverified"
    assert parsed_data.is_selected == ">"
    assert parsed_data.next_hop == "10.12.11.2"


def test_bgp_route_line2_valid() -> None:
    parsed_data = _bgp_route_line2().parseString(
        """
  valid                                            >10.12.11.2
        """
    )
    assert parsed_data.is_valid == "valid"
    assert parsed_data.is_selected == ">"
    assert parsed_data.next_hop == "10.12.11.2"
