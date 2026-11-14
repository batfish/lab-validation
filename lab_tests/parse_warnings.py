"""Assertions for the red flag warnings declared in parse_warnings.yaml."""

from collections.abc import Sequence

from lab_validation.validators.vendor_validator import ValidationError


def validate_parse_warnings(host: str, spec: dict, details: Sequence[str]) -> None:
    expected = []
    for key, severity in [
        ("expects_fatal_warning", "FATAL:"),
        ("expects_risky_warning", "RISK:"),
    ]:
        for entry in spec.get(key, []):
            if entry["host"] == host:
                expected.append((severity, entry["contains"]))
    for severity, contains in expected:
        if not any(d.startswith(severity) and contains in d for d in details):
            raise ValidationError(
                f"expected {severity} warning containing '{contains}' for '{host}' "
                f"but got: {list(details)}"
            )
    fatal = [d for d in details if d.startswith("FATAL:")]
    if fatal and not any(severity == "FATAL:" for severity, _ in expected):
        raise ValidationError(f"unexpected fatal warning for '{host}': {fatal}")
    if spec.get("strict", False):
        unexpected = [
            d
            for d in details
            if not any(
                d.startswith(severity) and contains in d
                for severity, contains in expected
            )
        ]
        if unexpected or len(details) != len(expected):
            raise ValidationError(
                f"expected {len(expected)} red flag warnings for '{host}', "
                f"got {list(details)}; unexpected: {unexpected}"
            )
