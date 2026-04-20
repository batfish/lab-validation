import pytest
from pyparsing import ParseException

from lab_validation.parsers.iosxr.grammar.route import _time


def test_time() -> None:
    # valid ones don't raise
    _time().parse_string("01:05:49")
    _time().parse_string("2d02h")
    _time().parse_string("30w4d")
    _time().parse_string("2y12w")
    # validate that invalid ones will
    with pytest.raises(ParseException):
        _time().parse_string("not-a-time")
