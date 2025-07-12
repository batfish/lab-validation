from lab_validation.parsers.a10.models.util import (
    canonicalize_interface,
    canonicalize_interface_opt,
)


def test_canonicalize_interface() -> None:
    assert canonicalize_interface("ve55") == "VirtualEthernet55"
    assert canonicalize_interface("ethernet1") == "Ethernet1"
    assert canonicalize_interface("trunk2") == "Trunk2"


def test_canonicalize_interface_opt() -> None:
    assert canonicalize_interface_opt(None) is None
    assert canonicalize_interface_opt("ethernet1") == "Ethernet1"
