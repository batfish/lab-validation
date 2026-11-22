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


def test_parse_show_bgp_vrf_all_ipv4_unicast_json_frr10() -> None:
    # FRR 10 writes the AS path as "path", the MED as "metric" and, for iBGP
    # paths, the local preference as "locPrf".
    text = """
    {
    "default":{
     "vrfId": 0,
     "vrfName": "default",
     "routerId": "1.1.1.1",
     "localAS": 65001,
     "routes": { "1.1.1.1/32": [{"valid":true,"bestpath":true,
       "selectionReason":"First path received","pathFrom":"external",
       "prefix":"1.1.1.1","prefixLen":32,"network":"1.1.1.1/32","version":1,
       "metric":0,"weight":32768,"peerId":"(unspec)","path":"","origin":"IGP",
       "nexthops":[{"ip":"0.0.0.0","hostname":"s1","afi":"ipv4","used":true}]}],
     "2.2.2.2/32": [{"valid":true,"pathFrom":"internal","prefix":"2.2.2.2",
       "prefixLen":32,"network":"2.2.2.2/32","version":4,"locPrf":200,
       "weight":0,"peerId":"192.168.12.3","path":"65002 65003",
       "origin":"incomplete",
       "nexthops":[{"ip":"192.168.12.3","hostname":"s2","afi":"ipv4",
         "used":true}]}]
     } , "totalRoutes": 2, "totalPaths": 2 }
    }
    """
    assert parse_show_ip_bgp_vrf_all_json(text) == [
        FrrBgpRoute(
            vrf="default",
            network="1.1.1.1/32",
            is_valid=True,
            is_multipath=False,
            is_bestpath=True,
            origin="IGP",
            path_from="external",
            peer_id="(unspec)",
            next_hops=[
                FrrBgpRouteNextHop(ip="0.0.0.0", afi="ipv4", scope=None, is_used=True)
            ],
            med=0,
            local_pref=None,
            as_path=(),
            weight=32768,
        ),
        FrrBgpRoute(
            vrf="default",
            network="2.2.2.2/32",
            is_valid=True,
            is_multipath=False,
            is_bestpath=False,
            origin="incomplete",
            path_from="internal",
            peer_id="192.168.12.3",
            next_hops=[
                FrrBgpRouteNextHop(
                    ip="192.168.12.3", afi="ipv4", scope=None, is_used=True
                )
            ],
            med=None,
            local_pref=200,
            as_path=(65002, 65003),
            weight=0,
        ),
    ]
