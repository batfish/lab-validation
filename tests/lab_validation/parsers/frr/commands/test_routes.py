import json

from lab_validation.parsers.frr.commands.routes import (
    _get_route,
    parse_show_ip_route_vrf_all_json,
)
from lab_validation.parsers.frr.models.routes import FrrIpRoute


def test_get_route_single() -> None:
    text = """
    {
      "prefix":"10.0.0.11\\/32",
      "protocol":"bgp",
      "selected":true,
      "distance":20,
      "metric":0,
      "uptime":"00:10:07",
      "nexthops":[
        {
          "fib":true,
          "ip":"10.127.0.8",
          "afi":"ipv4",
          "interfaceIndex":3,
          "interfaceName":"swp1",
          "active":true
        }
      ]
    }
    """
    routes = _get_route(json.loads(text))
    assert routes == [
        FrrIpRoute(
            vrf=None,
            network="10.0.0.11/32",
            next_hop_int="swp1",
            next_hop_ip="10.127.0.8",
            protocol="bgp",
            admin_distance=20,
            metric=0,
            active=True,
            blackhole=False,
        )
    ]


def test_get_route_ecmp() -> None:
    text = """
    {
      "prefix":"10.0.0.11\\/32",
      "protocol":"bgp",
      "selected":true,
      "distance":20,
      "metric":0,
      "uptime":"00:10:07",
      "nexthops":[
        {
          "fib":true,
          "ip":"10.127.0.8",
          "afi":"ipv4",
          "interfaceIndex":3,
          "interfaceName":"swp1",
          "active":true
        },
        {
          "fib":true,
          "ip":"10.127.1.8",
          "afi":"ipv4",
          "interfaceIndex":4,
          "interfaceName":"swp2",
          "active":true
        }
      ]
    }
    """
    routes = _get_route(json.loads(text))
    assert routes == [
        FrrIpRoute(
            vrf=None,
            network="10.0.0.11/32",
            next_hop_int="swp1",
            next_hop_ip="10.127.0.8",
            protocol="bgp",
            admin_distance=20,
            metric=0,
            active=True,
            blackhole=False,
        ),
        FrrIpRoute(
            vrf=None,
            network="10.0.0.11/32",
            next_hop_int="swp2",
            next_hop_ip="10.127.1.8",
            protocol="bgp",
            admin_distance=20,
            metric=0,
            active=True,
            blackhole=False,
        ),
    ]


def test_parse_show_ip_route_vrf_all_json() -> None:
    text = """
    {
      "10.0.0.11\\/32":[
        {
          "prefix":"10.0.0.11\\/32",
          "protocol":"bgp",
          "selected":true,
          "distance":20,
          "metric":0,
          "uptime":"00:10:07",
          "nexthops":[
            {
              "fib":true,
              "ip":"10.127.0.8",
              "afi":"ipv4",
              "interfaceIndex":3,
              "interfaceName":"swp1",
              "active":true
            }
          ]
        }
      ],
      "10.0.0.12\\/32":[
        {
          "prefix":"10.0.0.12\\/32",
          "protocol":"bgp",
          "selected":true,
          "distance":20,
          "metric":0,
          "uptime":"00:16:12",
          "nexthops":[
            {
              "fib":true,
              "ip":"10.127.0.8",
              "afi":"ipv4",
              "interfaceIndex":3,
              "interfaceName":"swp1",
              "active":true
            },
            {
              "fib":true,
              "ip":"10.127.1.8",
              "afi":"ipv4",
              "interfaceIndex":4,
              "interfaceName":"swp2",
              "active":true
            }
          ]
        }
      ]
    }
    {
      "10.0.0.20\\/32":[
        {
          "prefix":"10.0.0.20\\/32",
          "protocol":"bgp",
          "vrfId":9,
          "selected":true,
          "distance":20,
          "metric":0,
          "uptime":"00:10:07",
          "nexthops":[
            {
              "fib":true,
              "ip":"10.127.0.20",
              "afi":"ipv4",
              "interfaceIndex":20,
              "interfaceName":"swp20",
              "active":true
            }
          ]
        }
      ]
    }
    """
    routes = parse_show_ip_route_vrf_all_json(text)
    assert routes == [
        FrrIpRoute(
            vrf=None,
            network="10.0.0.11/32",
            next_hop_int="swp1",
            next_hop_ip="10.127.0.8",
            protocol="bgp",
            admin_distance=20,
            metric=0,
            active=True,
            blackhole=False,
        ),
        FrrIpRoute(
            vrf=None,
            network="10.0.0.12/32",
            next_hop_int="swp1",
            next_hop_ip="10.127.0.8",
            protocol="bgp",
            admin_distance=20,
            metric=0,
            active=True,
            blackhole=False,
        ),
        FrrIpRoute(
            vrf=None,
            network="10.0.0.12/32",
            next_hop_int="swp2",
            next_hop_ip="10.127.1.8",
            protocol="bgp",
            admin_distance=20,
            metric=0,
            active=True,
            blackhole=False,
        ),
        FrrIpRoute(
            vrf=9,
            network="10.0.0.20/32",
            next_hop_int="swp20",
            next_hop_ip="10.127.0.20",
            protocol="bgp",
            admin_distance=20,
            metric=0,
            active=True,
            blackhole=False,
        ),
    ]


def test_parse_show_ip_route_vrf_all_json_directly_connected() -> None:
    text = """
    {
      "10.127.0.8\\/31":[
        {
          "prefix":"10.127.0.8\\/31",
          "protocol":"connected",
          "selected":true,
          "uptime":"00:16:18",
          "nexthops":[
            {
              "fib":true,
              "directlyConnected":true,
              "interfaceIndex":3,
              "interfaceName":"swp1",
              "active":true
            }
          ]
        }
      ]
    }
    """
    routes = parse_show_ip_route_vrf_all_json(text)
    assert routes == [
        FrrIpRoute(
            vrf=None,
            network="10.127.0.8/31",
            next_hop_int="swp1",
            next_hop_ip=None,
            protocol="connected",
            admin_distance=0,
            metric=0,
            active=True,
            blackhole=False,
        )
    ]


def test_parse_show_ip_route_vrf_all_json_active_inactive() -> None:
    text = """
    {
      "10.10.40.0\\/24":[
        {
          "prefix":"10.10.40.0\\/24",
          "protocol":"bgp",
          "distance":20,
          "metric":0,
          "uptime":"00:17:53",
          "nexthops":[
            {
              "ip":"10.10.40.1",
              "afi":"ipv4"
            }
          ]
        },
        {
          "prefix":"10.10.40.0\\/24",
          "protocol":"connected",
          "selected":true,
          "uptime":"00:20:13",
          "nexthops":[
            {
              "fib":true,
              "directlyConnected":true,
              "interfaceIndex":3,
              "interfaceName":"swp1",
              "active":true
            }
          ]
        }
      ]
    }
    """
    routes = parse_show_ip_route_vrf_all_json(text)
    assert routes == [
        FrrIpRoute(
            vrf=None,
            network="10.10.40.0/24",
            next_hop_int=None,
            next_hop_ip="10.10.40.1",
            protocol="bgp",
            admin_distance=20,
            metric=0,
            active=False,
            blackhole=False,
        ),
        FrrIpRoute(
            vrf=None,
            network="10.10.40.0/24",
            next_hop_int="swp1",
            next_hop_ip=None,
            protocol="connected",
            admin_distance=0,
            metric=0,
            active=True,
            blackhole=False,
        ),
    ]


def test_parse_show_ip_route_vrf_all_json_discard() -> None:
    text = """
    {
      "174.0.0.0\\/8":[
        {
          "prefix":"174.0.0.0\\/8",
          "protocol":"ospf",
          "selected":true,
          "distance":110,
          "metric":0,
          "uptime":"00:30:37",
          "nexthops":[
            {
              "fib":true,
              "unreachable":true,
              "blackhole":true,
              "active":true
            }
          ]
        }
      ]
    }
    """
    routes = parse_show_ip_route_vrf_all_json(text)
    assert routes == [
        FrrIpRoute(
            vrf=None,
            network="174.0.0.0/8",
            next_hop_int=None,
            next_hop_ip=None,
            protocol="ospf",
            admin_distance=110,
            metric=0,
            active=True,
            blackhole=True,
        )
    ]
