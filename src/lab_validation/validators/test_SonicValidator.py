from pathlib import Path

from lab_validation.parsers.frr.models.routes import FrrIpRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.runtime_data import (
    InterfaceRuntimeData,
)

from .SonicValidator import SonicValidator

# Real output from a containerlab sonic-vm node (SONiC.202605), trimmed.
SHOW_INTERFACES_STATUS = """\
  Interface            Lanes    Speed    MTU    FEC           Alias    Vlan    Oper    Admin    Type    Asym PFC
-----------  ---------------  -------  -----  -----  --------------  ------  ------  -------  ------  ----------
  Ethernet0      25,26,27,28      40G   9100    N/A    fortyGigE0/0  routed      up       up     N/A         N/A
  Ethernet8      33,34,35,36      40G   9100    N/A    fortyGigE0/8  routed    down       up     N/A         N/A
"""  # noqa: E501


def _validator(tmp_path: Path) -> SonicValidator:
    (tmp_path / "show_interfaces_status.txt").write_text(SHOW_INTERFACES_STATUS)
    return SonicValidator(tmp_path)


def _batfish_iface(name: str, active: bool) -> InterfaceProperties:
    return InterfaceProperties(
        name=name,
        active=active,
        all_prefixes=[],
        allowed_vlans=None,
        bandwidth=int(40e9),
        description=None,
        mtu=9100,
        speed=int(40e9),
        switchport=False,
        switchport_mode="NONE",
        vrf="default",
    )


def test_get_runtime_data(tmp_path: Path) -> None:
    assert _validator(tmp_path).get_runtime_data().interfaces == {
        "Ethernet0": InterfaceRuntimeData(bandwidth=40e9, lineUp=True, speed=40e9),
        "Ethernet8": InterfaceRuntimeData(bandwidth=40e9, lineUp=False, speed=40e9),
    }


def test_get_runtime_data_without_status(tmp_path: Path) -> None:
    assert SonicValidator(tmp_path).get_runtime_data().interfaces == {}


def test_validate_interface_properties_match(tmp_path: Path) -> None:
    batfish = [
        _batfish_iface("Ethernet0", active=True),
        _batfish_iface("Ethernet8", active=False),
        # Not a front-panel port, so absent from 'show interfaces status'.
        _batfish_iface("Loopback0", active=True),
    ]
    assert _validator(tmp_path).validate_interface_properties(batfish, set()) == {
        "batfish_extra": {},
        "batfish_missing": {},
        "batfish_mismatch": {},
    }


def test_validate_interface_properties_oper_down_mismatch(tmp_path: Path) -> None:
    batfish = [
        _batfish_iface("Ethernet0", active=True),
        _batfish_iface("Ethernet8", active=True),
    ]
    diffs = _validator(tmp_path).validate_interface_properties(batfish, set())
    assert diffs["batfish_mismatch"] == {
        "Ethernet8": {"active": "Batfish: True, show_data: False"}
    }


def test_show_route_processed_drops_host_only_routes(tmp_path: Path) -> None:
    def route(network: str, protocol: str, interface: str) -> FrrIpRoute:
        return FrrIpRoute(
            vrf="default",
            network=network,
            protocol=protocol,
            next_hop_ip=None,
            admin_distance=0,
            next_hop_int=interface,
            metric=0,
            active=True,
            blackhole=False,
        )

    loopback = route("1.1.1.1/32", "connected", "Loopback0")
    routes = [
        loopback,
        route("0.0.0.0/0", "kernel", "eth0"),
        route("10.0.0.0/24", "connected", "eth0"),
    ]
    assert _validator(tmp_path)._show_route_processed(routes) == [loopback]
