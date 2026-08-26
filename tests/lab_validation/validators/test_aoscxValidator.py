from pybatfish.datamodel.route import NextHopIp

from lab_validation.validators.AoscxValidator import AoscxValidator
from lab_validation.validators.batfish_models.routes import MainRibRoute


def _write_route_output(tmp_path):
    (tmp_path / "show_ip_route.txt").write_text(
        """\
VRF: default
Prefix              Nexthop                                  Interface     VRF(egress)       Origin/   Distance/    Age
10.0.0.0/31         -                                        1/1/1         -                 C         [0/0]        -
2.2.2.2/32          10.0.0.1                                 1/1/1         -                 S         [1/0]        -
"""
    )


def test_route_parser_normalizes_aoscx_protocols(tmp_path) -> None:
    _write_route_output(tmp_path)

    routes = AoscxValidator(tmp_path)._routes()

    assert [(route.network, route.protocol) for route in routes] == [
        ("10.0.0.0/31", "connected"),
        ("2.2.2.2/32", "static"),
    ]


def test_route_validation_reports_device_only_routes(tmp_path) -> None:
    _write_route_output(tmp_path)
    validator = AoscxValidator(tmp_path)
    expected = [
        MainRibRoute(
            vrf="default",
            network="2.2.2.2/32",
            next_hop=NextHopIp("10.0.0.1"),
            protocol="static",
            metric=0,
            admin=1,
            tag=None,
        )
    ]

    assert "10.0.0.0/31" in str(validator.validate_main_rib_routes(expected))
