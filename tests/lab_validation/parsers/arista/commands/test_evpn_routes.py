from lab_validation.parsers.arista.commands.evpn_routes import parse_show_bgp_evpn_json
from lab_validation.parsers.arista.models.routes import AristaEvpnRoute


def test_parse_show_bgp_evpn_json() -> None:
    text = """

{
    "routerId": "1.1.1.3",
    "vrf": "default",
    "asn": 65001,
    "evpnRoutes": {
        "RD: 2.2.2.2:4001 ip-prefix 192.168.61.8/32": {
            "totalPaths": 2,
            "routeKeyDetail": {
                "ipGenPrefix": "192.168.61.8/32",
                "rd": "2.2.2.2:4001",
                "nlriType": "ip-prefix"
            },
            "evpnRoutePaths": [
                {
                    "asPathEntry": {
                        "asPath": "65000 65100 65200 i",
                        "asPathType": "External"
                    },
                    "localPreference": 100,
                    "weight": 0,
                    "nextHop": "2.2.2.2",
                    "routeType": {
                        "atomicAggregator": false,
                        "origin": "Igp",
                        "localAgg": false,
                        "waitForConvergence": false,
                        "suppressed": false,
                        "queued": false,
                        "valid": true,
                        "ecmpContributor": false,
                        "active": true,
                        "stale": false,
                        "ecmp": false,
                        "backup": false,
                        "ecmpHead": false
                    }
                },
                {
                    "asPathEntry": {
                        "asPath": "65000 65100 i",
                        "asPathType": "Internal"
                    },
                    "localPreference": 10,
                    "weight": 20,
                    "nextHop": "3.2.2.2",
                    "routeType": {
                        "atomicAggregator": false,
                        "origin": "Igp",
                        "localAgg": false,
                        "waitForConvergence": false,
                        "suppressed": false,
                        "queued": false,
                        "valid": true,
                        "ecmpContributor": false,
                        "active": false,
                        "stale": false,
                        "ecmp": false,
                        "backup": false,
                        "ecmpHead": false
                    }
                }
            ]
        },
        "RD: 3.2.2.2:4001 ip-prefix 100.100.100.100/32": {
            "totalPaths": 2,
            "routeKeyDetail": {
                "ipGenPrefix": "100.100.100.100/32",
                "rd": "3.2.2.2:4001",
                "nlriType": "ip-prefix"
            },
            "evpnRoutePaths": [
                {
                    "asPathEntry": {
                        "asPath": "65000 i",
                        "asPathType": "External"
                    },
                    "localPreference": 100,
                    "weight": 0,
                    "nextHop": "",
                    "routeType": {
                        "atomicAggregator": false,
                        "origin": "Igp",
                        "localAgg": false,
                        "waitForConvergence": false,
                        "suppressed": false,
                        "queued": false,
                        "valid": true,
                        "ecmpContributor": false,
                        "active": true,
                        "stale": false,
                        "ecmp": false,
                        "backup": false,
                        "ecmpHead": false
                    }
                }
            ]
        }
    }
}

"""

    routes = parse_show_bgp_evpn_json(text)
    assert routes == [
        AristaEvpnRoute(
            vrf="default",
            network="192.168.61.8/32",
            as_path=(65000, 65100, 65200),
            as_path_type="External",
            local_preference=100,
            weight=0,
            next_hop_ip="2.2.2.2",
            is_active=True,
            route_distinguisher="2.2.2.2:4001",
            origin="Igp",
        ),
        AristaEvpnRoute(
            vrf="default",
            network="192.168.61.8/32",
            as_path=(65000, 65100),
            as_path_type="Internal",
            local_preference=10,
            weight=20,
            next_hop_ip="3.2.2.2",
            is_active=False,
            route_distinguisher="2.2.2.2:4001",
            origin="Igp",
        ),
        AristaEvpnRoute(
            vrf="default",
            network="100.100.100.100/32",
            as_path=(65000,),
            as_path_type="External",
            local_preference=100,
            weight=0,
            next_hop_ip=None,
            is_active=True,
            route_distinguisher="3.2.2.2:4001",
            origin="Igp",
        ),
    ]
