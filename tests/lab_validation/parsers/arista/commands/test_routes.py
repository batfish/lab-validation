from lab_validation.parsers.arista.commands.routes import (
    parse_show_ip_route_vrf_all_json,
)
from lab_validation.parsers.arista.models.routes import AristaIpRoute


def test_parse_show_ip_route_vrf_all_json() -> None:
    text = """
{
    "vrfs": {
        "default": {
            "routes": {
                "10.10.40.0/24": {"kernelProgrammed": true, "directlyConnected": false, "preference": 200, "routeAction": "forward", "vias": [{"interface": "Ethernet1", "nexthopAddr": "10.10.30.1"}], "metric": 0, "hardwareProgrammed": true, "routeType": "eBGP"},
                "10.10.30.0/24": {"kernelProgrammed": true, "directlyConnected": true, "routeAction": "forward", "vias": [{"interface": "Ethernet2"}], "hardwareProgrammed": true, "routeType": "connected"},
                "172.17.211.0/24": {"kernelProgrammed": true, "directlyConnected": false, "preference": 1, "routeAction": "forward", "vias": [{"interface": "Ethernet3", "nexthopAddr": "10.10.30.2"}], "metric": 0, "hardwareProgrammed": true, "routeType": "static"},
                "172.17.252.0/24": {"kernelProgrammed": true, "directlyConnected": true, "routeAction": "forward", "vias": [{"interface": "Ethernet4"}], "hardwareProgrammed": true, "routeType": "static"}
            },
            "allRoutesProgrammedKernel": true,
            "routingDisabled": false,
            "allRoutesProgrammedHardware": true,
            "defaultRouteState": "notSet"
        },
        "cust10": {
            "routes": {
                "1.1.4.10/32": {"kernelProgrammed": true, "directlyConnected": true, "routeAction": "forward", "vias": [{"interface": "Loopback10"}], "hardwareProgrammed": true, "routeType": "connected"}
            },
            "allRoutesProgrammedKernel": true,
            "routingDisabled": false,
            "allRoutesProgrammedHardware": true,
            "defaultRouteState": "notSet"
        }
    }
}
    """
    routes = parse_show_ip_route_vrf_all_json(text)
    assert routes == [
        AristaIpRoute(
            vrf="default",
            network="10.10.40.0/24",
            next_hop_int="Ethernet1",
            next_hop_ip="10.10.30.1",
            protocol="eBGP",
            preference=200,
            metric=0,
            vni=None,
            vtep_ip=None,
        ),
        AristaIpRoute(
            vrf="default",
            network="10.10.30.0/24",
            next_hop_int="Ethernet2",
            next_hop_ip=None,
            protocol="connected",
            preference=None,
            metric=None,
            vni=None,
            vtep_ip=None,
        ),
        AristaIpRoute(
            vrf="default",
            network="172.17.211.0/24",
            next_hop_int="Ethernet3",
            next_hop_ip="10.10.30.2",
            protocol="static",
            preference=1,
            metric=0,
            vni=None,
            vtep_ip=None,
        ),
        AristaIpRoute(
            vrf="default",
            network="172.17.252.0/24",
            next_hop_int="Ethernet4",
            next_hop_ip=None,
            protocol="static",
            preference=None,
            metric=None,
            vni=None,
            vtep_ip=None,
        ),
        AristaIpRoute(
            vrf="cust10",
            network="1.1.4.10/32",
            next_hop_int="Loopback10",
            next_hop_ip=None,
            protocol="connected",
            preference=None,
            metric=None,
            vni=None,
            vtep_ip=None,
        ),
    ]


def test_parse_show_ip_route_vrf_all_json_no_interface() -> None:
    text = """
{
    "vrfs": {
        "default": {
            "routes": {
                "10.10.40.0/24": {"kernelProgrammed": true, "directlyConnected": false, "preference": 200, "routeAction": "forward", "vias": [{"nexthopAddr": "10.10.30.1"}], "metric": 0, "hardwareProgrammed": true, "routeType": "eBGP"}
            },
            "allRoutesProgrammedKernel": true,
            "routingDisabled": false,
            "allRoutesProgrammedHardware": true,
            "defaultRouteState": "notSet"
        }
    }
}
    """
    routes = parse_show_ip_route_vrf_all_json(text)
    assert routes == [
        AristaIpRoute(
            vrf="default",
            network="10.10.40.0/24",
            next_hop_int=None,
            next_hop_ip="10.10.30.1",
            protocol="eBGP",
            preference=200,
            metric=0,
            vni=None,
            vtep_ip=None,
        )
    ]


def test_parse_show_ip_route_vrf_all_json_vtep() -> None:
    text = """
{
    "vrfs": {
        "default": {
            "routes": {
                "10.3.255.6/32": {"kernelProgrammed": true, "directlyConnected": false, "routeAction": "forward", "routeLeaked": false, "vias": [{"vtepAddr": "192.168.254.6", "nexthopAddr": "", "routerMac": "0c:d0:34:bd:f7:54", "vni": 50301}], "metric": 0, "hardwareProgrammed": true, "routeType": "eBGP", "preference": 200}
            },
            "allRoutesProgrammedKernel": true,
            "routingDisabled": false,
            "allRoutesProgrammedHardware": true,
            "defaultRouteState": "notSet"
        }
    }
}
    """
    routes = parse_show_ip_route_vrf_all_json(text)
    assert routes == [
        AristaIpRoute(
            vrf="default",
            network="10.3.255.6/32",
            next_hop_int=None,
            next_hop_ip="",
            protocol="eBGP",
            preference=200,
            metric=0,
            vni=50301,
            vtep_ip="192.168.254.6",
        )
    ]
