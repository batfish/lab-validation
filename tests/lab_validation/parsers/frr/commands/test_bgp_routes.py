from lab_validation.parsers.frr.commands.bgp_routes import (
    parse_show_ip_bgp_vrf_all_json,
)
from lab_validation.parsers.frr.models.routes import FrrBgpRoute, FrrBgpRouteNextHop


def test_parse_show_ip_bgp_vrf_all_json() -> None:
    text = """
    {
      "default": {
        "vrfId": 0,
        "vrfName": "default",
        "tableVersion": 23,
        "routerId": "10.0.0.11",
        "routes": {
          "10.0.0.12/32": [
            {
              "valid": true,
              "multipath": true,
              "pathFrom": "external",
              "prefix": "10.0.0.12",
              "prefixLen": 32,
              "weight": 0,
              "peerId": "fe80::a00:27ff:fe8f:2faa",
              "aspath": "65000 65102",
              "origin": "incomplete",
              "nexthops": [
                {
                  "ip": "fe80::a00:27ff:fe8f:2faa",
                  "afi": "ipv6",
                  "scope": "global",
                  "used": true
                },
                {
                  "ip": "fe80::a00:27ff:fe8f:2faa",
                  "afi": "ipv6",
                  "scope": "link-local"
                }
              ]
            },
            {
              "valid": true,
              "bestpath": true,
              "pathFrom": "external",
              "prefix": "10.0.0.12",
              "prefixLen": 32,
              "weight": 0,
              "peerId": "fe80::a00:27ff:fe4d:7b54",
              "aspath": "65000 65102",
              "origin": "incomplete",
              "nexthops": [
                {
                  "ip": "fe80::a00:27ff:fe4d:7b54",
                  "afi": "ipv6",
                  "scope": "global",
                  "used": true
                },
                {
                  "ip": "fe80::a00:27ff:fe4d:7b54",
                  "afi": "ipv6",
                  "scope": "link-local"
                }
              ]
            }
          ]
        }
      },
      "internet-vrf": {
        "vrfId": 11,
        "vrfName": "internet-vrf",
        "tableVersion": 16,
        "routerId": "10.0.0.101",
        "routes": {
          "0.0.0.0/0": [
            {
              "valid": true,
              "bestpath": true,
              "pathFrom": "external",
              "prefix": "0.0.0.0",
              "prefixLen": 0,
              "weight": 0,
              "peerId": "169.254.127.0",
              "aspath": "25253",
              "origin": "IGP",
              "nexthops": [
                {
                  "ip": "169.254.127.0",
                  "afi": "ipv4",
                  "used": true
                }
              ]
            }
          ]
        }
      }
    }
    """
    routes = parse_show_ip_bgp_vrf_all_json(text)
    assert routes == [
        FrrBgpRoute(
            vrf="default",
            network="10.0.0.12/32",
            is_valid=True,
            is_multipath=True,
            is_bestpath=False,
            origin="incomplete",
            path_from="external",
            peer_id="fe80::a00:27ff:fe8f:2faa",
            next_hops=[
                FrrBgpRouteNextHop(
                    ip="fe80::a00:27ff:fe8f:2faa",
                    afi="ipv6",
                    scope="global",
                    is_used=True,
                ),
                FrrBgpRouteNextHop(
                    ip="fe80::a00:27ff:fe8f:2faa",
                    afi="ipv6",
                    scope="link-local",
                    is_used=False,
                ),
            ],
            med=None,
            as_path=(65000, 65102),
            weight=0,
        ),
        FrrBgpRoute(
            vrf="default",
            network="10.0.0.12/32",
            is_valid=True,
            is_multipath=False,
            is_bestpath=True,
            origin="incomplete",
            path_from="external",
            peer_id="fe80::a00:27ff:fe4d:7b54",
            next_hops=[
                FrrBgpRouteNextHop(
                    ip="fe80::a00:27ff:fe4d:7b54",
                    afi="ipv6",
                    scope="global",
                    is_used=True,
                ),
                FrrBgpRouteNextHop(
                    ip="fe80::a00:27ff:fe4d:7b54",
                    afi="ipv6",
                    scope="link-local",
                    is_used=False,
                ),
            ],
            med=None,
            as_path=(65000, 65102),
            weight=0,
        ),
        FrrBgpRoute(
            vrf="internet-vrf",
            network="0.0.0.0/0",
            is_valid=True,
            is_multipath=False,
            is_bestpath=True,
            origin="IGP",
            path_from="external",
            peer_id="169.254.127.0",
            next_hops=[
                FrrBgpRouteNextHop(
                    ip="169.254.127.0", afi="ipv4", scope=None, is_used=True
                )
            ],
            med=None,
            as_path=(25253,),
            weight=0,
        ),
    ]
