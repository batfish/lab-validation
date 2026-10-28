from pathlib import Path

from lab_validation.parsers.frr.models.routes import FrrIpRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)

from .FrrValidator import FrrValidator

# Real output from a containerlab FRR 10.7.1 node, trimmed.
SHOW_INTERFACE_VRF_ALL = """\
Interface eth0 is up, line protocol is up
  Link ups:       0    last: (never)
  Link downs:     0    last: (never)
  vrf: default
  index 2 metric 0 mtu 1500 speed 10000 txqlen 0
  flags: <UP,LOWER_UP,BROADCAST,RUNNING,MULTICAST>
  Type: Ethernet
  inet 172.20.20.5/24
  Interface Type VETH
Interface eth1 is up, line protocol is up
  Link ups:       0    last: (never)
  Link downs:     0    last: (never)
  vrf: default
  index 33 metric 0 mtu 1500 speed 10000 txqlen 0
  flags: <UP,LOWER_UP,BROADCAST,RUNNING,MULTICAST>
  Type: Ethernet
  inet 10.0.1.0/31
  Interface Type VETH
"""

SHOW_IP_ROUTE_VRF_ALL_JSON = """\
{
"default":{
"10.0.1.0/31":[{"prefix":"10.0.1.0/31","protocol":"connected","selected":true,
  "distance":0,"metric":0,"vrfName":"default",
  "nexthops":[{"directlyConnected":true,"interfaceName":"eth1","active":true}]}],
"10.0.1.0/32":[{"prefix":"10.0.1.0/32","protocol":"local","selected":true,
  "distance":0,"metric":0,"vrfName":"default",
  "nexthops":[{"directlyConnected":true,"interfaceName":"eth1","active":true}]}],
"172.20.20.0/24":[{"prefix":"172.20.20.0/24","protocol":"connected","selected":true,
  "distance":0,"metric":0,"vrfName":"default",
  "nexthops":[{"directlyConnected":true,"interfaceName":"eth0","active":true}]}]
}
}
"""


def _validator(tmp_path: Path) -> FrrValidator:
    (tmp_path / FrrValidator.SHOW_INTERFACES_FILENAME_TXT).write_text(
        SHOW_INTERFACE_VRF_ALL
    )
    (tmp_path / FrrValidator.SHOW_ROUTE_FILENAME_TXT).write_text(
        SHOW_IP_ROUTE_VRF_ALL_JSON
    )
    return FrrValidator(tmp_path)


def _batfish_iface(name: str, mtu: int) -> InterfaceProperties:
    return InterfaceProperties(
        name=name,
        active=True,
        all_prefixes=[],
        allowed_vlans=None,
        bandwidth=int(10e9),
        description=None,
        mtu=mtu,
        speed=int(10e9),
        switchport=False,
        switchport_mode="NONE",
        vrf="default",
    )


def test_validate_interface_properties_skips_management_port(tmp_path: Path) -> None:
    batfish = [_batfish_iface("eth1", mtu=1500)]
    assert _validator(tmp_path).validate_interface_properties(batfish, set()) == {}


def test_validate_interface_properties_mismatch(tmp_path: Path) -> None:
    batfish = [_batfish_iface("eth1", mtu=9500)]
    assert _validator(tmp_path).validate_interface_properties(batfish, set()) == {
        "batfish_mismatch": {"eth1": {"mtu": "Batfish: 9500, show_data: 1500"}}
    }


def test_show_route_processed_drops_local_and_management_routes(
    tmp_path: Path,
) -> None:
    validator = _validator(tmp_path)
    assert validator._show_route_processed(validator._parse_routes()) == [
        FrrIpRoute(
            vrf="default",
            network="10.0.1.0/31",
            protocol="connected",
            next_hop_ip=None,
            admin_distance=0,
            next_hop_int="eth1",
            metric=0,
            active=True,
            blackhole=False,
        )
    ]
