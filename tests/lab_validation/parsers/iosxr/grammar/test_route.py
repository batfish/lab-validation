import pytest
from pyparsing import ParseException

from lab_validation.parsers.iosxr.grammar.route import _time


def test_time() -> None:
    # valid ones don't raise
    _time().parseString("01:05:49")
    _time().parseString("2d02h")
    _time().parseString("30w4d")
    _time().parseString("2y12w")
    # validate that invalid ones will
    with pytest.raises(ParseException):
        _time().parseString("not-a-time")
