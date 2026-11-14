import pytest

from lab_tests.parse_warnings import validate_parse_warnings
from lab_validation.validators.vendor_validator import ValidationError


@pytest.mark.parametrize("severity", ["fatal", "risky"])
def test_expected_severity(severity):
    prefix = "FATAL:" if severity == "fatal" else "RISK:"
    spec = {
        "strict": True,
        f"expects_{severity}_warning": [{"host": "dut", "contains": "filter-A"}],
    }
    validate_parse_warnings("dut", spec, [f"{prefix} filter-A"])
    with pytest.raises(ValidationError):
        validate_parse_warnings("dut", spec, [])
    wrong = "RISK:" if severity == "fatal" else "FATAL:"
    with pytest.raises(ValidationError):
        validate_parse_warnings("dut", spec, [f"{wrong} filter-A"])


def test_multiple_warnings_on_one_host():
    spec = {
        "strict": True,
        "expects_risky_warning": [
            {"host": "dut", "contains": "filter-A"},
            {"host": "dut", "contains": "filter-B"},
        ],
    }
    validate_parse_warnings("dut", spec, ["RISK: filter-A", "RISK: filter-B"])
    with pytest.raises(ValidationError):
        validate_parse_warnings("dut", spec, ["RISK: filter-A"])


@pytest.mark.parametrize(
    "details",
    [
        ["FATAL: unrelated"],
        ["RISK: unrelated"],
        ["Unrecognized syntax"],
    ],
)
def test_strict_no_warning_control(details):
    validate_parse_warnings("dut", {"strict": True}, [])
    with pytest.raises(ValidationError):
        validate_parse_warnings("dut", {"strict": True}, details)


@pytest.mark.parametrize(
    "details",
    [
        ["RISK: unrelated"],
        ["RISK: filter-A", "RISK: unrelated"],
        ["RISK: filter-A", "RISK: filter-A"],
    ],
)
def test_strict_unexpected_warning(details):
    spec = {
        "strict": True,
        "expects_risky_warning": [{"host": "dut", "contains": "filter-A"}],
    }
    with pytest.raises(ValidationError):
        validate_parse_warnings("dut", spec, details)


def test_warning_expected_on_other_host_does_not_match():
    spec = {
        "strict": True,
        "expects_risky_warning": [{"host": "other", "contains": "filter-A"}],
    }
    with pytest.raises(ValidationError):
        validate_parse_warnings("dut", spec, ["RISK: filter-A"])


def test_default_remains_no_fatal():
    validate_parse_warnings("dut", {}, [])
    validate_parse_warnings("dut", {}, ["RISK: existing"])
    with pytest.raises(ValidationError):
        validate_parse_warnings("dut", {}, ["FATAL: existing"])
