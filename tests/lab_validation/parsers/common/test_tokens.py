import pytest
from pyparsing import ParseException

from lab_validation.parsers.common.tokens import dec, ip, prefix


def test_ip_parsing() -> None:
    assert ip.parse_string("1.1.1.1").asList() == ["1.1.1.1"]
    assert ip.parse_string("0.0.0.0").asList() == ["0.0.0.0"]
    assert ip.parse_string("255.255.255.255").asList() == ["255.255.255.255"]
    assert ip.parse_string("255.255.255.256").asList() == ["255.255.255.25"]
    assert ip.parse_string("1.2.3.4.5").asList() == ["1.2.3.4"]
    with pytest.raises(ParseException):
        ip.parse_string("355.255.255.255").asList()
    with pytest.raises(ParseException):
        ip.parse_string("1.2.3.4.5", parseAll=True).asList()
    with pytest.raises(ParseException):
        ip.parse_string("1.1.1. 1").asList()
    with pytest.raises(ParseException):
        ip.parse_string("1.1.1.").asList()


def test_prefix_parsing() -> None:
    assert prefix.parse_string("1.1.1.1/32", parseAll=True).asList() == ["1.1.1.1/32"]
    assert prefix.parse_string("14.0.0.0/8", parseAll=True).asList() == ["14.0.0.0/8"]
    assert prefix.parse_string("0.0.0.0/0", parseAll=True).asList() == ["0.0.0.0/0"]
    with pytest.raises(ParseException):
        prefix.parse_string("0.0.0.0/45", parseAll=True).asList()
    with pytest.raises(ParseException):
        prefix.parse_string("0.0.0/45", parseAll=True)
    with pytest.raises(ParseException):
        prefix.parse_string("0/0", parseAll=True)
    with pytest.raises(ParseException):
        prefix.parse_string("1.2.3.4.5/24", parseAll=True)
    with pytest.raises(ParseException):
        prefix.parse_string("1.1.1.1/33", parseAll=True).asList()


def test_dec_parsing() -> None:
    assert dec.parse_string("0").asList() == [0]
    assert dec.parse_string("004").asList() == [4]
    with pytest.raises(ParseException):
        dec.parse_string("-5").asList()
