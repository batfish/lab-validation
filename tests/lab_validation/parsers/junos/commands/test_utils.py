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
