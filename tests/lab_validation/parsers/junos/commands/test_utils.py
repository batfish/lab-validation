from lab_validation.parsers.junos.commands.utils import (
    _parse_table_header,
    remove_unused_lines,
)


def test_remove_unused_lines() -> None:
    text = """
    {
        route: []
    }
    {master:0}
    """

    result = remove_unused_lines(text)
    assert (
        result
        == """
    {
        route: []
    }
    """
    )


def test_remove_unused_lines_empty() -> None:
    text = "{master:0}"

    result = remove_unused_lines(text)
    assert result == ""


def test_parse_table_header_default() -> None:
    vrf, ip_version = _parse_table_header("inet.0")
    assert vrf == "default" and ip_version == "inet.0"


def test_parse_table_header_vrf_ipv4() -> None:
    vrf, ip_version = _parse_table_header("vrf.inet.0")
    assert vrf == "vrf" and ip_version == "inet.0"


def test_parse_table_header_vrf_ipv6() -> None:
    vrf, ip_version = _parse_table_header("vrf.inet6.0")
    assert vrf == "vrf" and ip_version == "inet6.0"


def test_parse_table_header_evpn() -> None:
    vrf, rib = _parse_table_header("bgp.evpn.0")
    assert vrf == "default" and rib == "bgp.evpn.0"


def test_parse_table_header_vrf_evpn() -> None:
    vrf, rib = _parse_table_header("TENANT-A.evpn.0")
    assert vrf == "TENANT-A" and rib == "evpn.0"


def test_parse_table_header_mpls() -> None:
    vrf, rib = _parse_table_header("mpls.0")
    assert vrf == "default" and rib == "mpls.0"


def test_parse_table_header_mgmt_junos() -> None:
    vrf, rib = _parse_table_header("mgmt_junos.inet.0")
    assert vrf == "mgmt_junos" and rib == "inet.0"
