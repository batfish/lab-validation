import re
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional

import attr
from cerberus import Validator


class SkipType(Enum):
    """Different ways of skipping a test."""

    XFAIL = "xfail"
    DONT_RUN = "dont_run"

    @staticmethod
    def of(value: str) -> "SkipType":
        return SkipType[value.upper()]


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class Skip(object):
    """Details about how and why the test should be skipped."""

    SCHEMA: ClassVar = {
        "skip_type": {"type": "string", "allowed": [e.value for e in SkipType]},
        "reason": {"type": "string"},
    }

    # By default, run the test and XFAIL, give no reason.
    skip_type: SkipType = attr.ib(default=SkipType.XFAIL)
    reason: Optional[str] = attr.ib(default=None)

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> "Skip":
        st = d.get("skip_type")
        return Skip(
            skip_type=SkipType.XFAIL if st is None else SkipType.of(st),
            reason=d.get("reason"),
        )


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class SickbayEntry(object):
    """A single entry in the lab Sickbay"""

    SCHEMA: ClassVar = {
        # For now require both match conditions to make code simpler. Can be relaxed later.
        "test_name": {"type": "string", "required": True},
        "hostname": {"type": "string"},
        "skip": {"type": "dict", "schema": Skip.SCHEMA},
    }

    test_name: str
    hostname: Optional[str]
    skip: Skip = attr.ib(factory=Skip)

    def matches(self, test_name: str, hostname: Optional[str]) -> bool:
        if test_name is None and hostname is None:
            raise ValueError("Invalid criteria to match sickbay entry")
        return test_name == self.test_name and (
            self.hostname is None
            or (hostname is not None and bool(re.fullmatch(self.hostname, hostname)))
        )

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SickbayEntry":
        skip = d.get("skip")
        return SickbayEntry(
            test_name=d["test_name"],
            hostname=d.get("hostname"),
            skip=Skip.from_dict(skip) if skip is not None else Skip(),
        )


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class Sickbay(object):
    """Represents a set of sickbayed tests for a single lab."""

    SCHEMA: ClassVar = {
        "entries": {
            "type": "list",
            "schema": {"type": "dict", "schema": SickbayEntry.SCHEMA},
        },
    }

    entries: List[SickbayEntry]

    def matches(
        self, test_name: str, hostname: Optional[str]
    ) -> Optional[SickbayEntry]:
        """Return first matching sickbay entry"""
        return next((e for e in self.entries if e.matches(test_name, hostname)), None)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Sickbay":
        cls._validate_data(d)
        return Sickbay(
            entries=[SickbayEntry.from_dict(e) for e in d.get("entries", [])]
        )

    @classmethod
    def _validate_data(cls, d: Dict[str, Any]) -> None:
        v = Validator()
        v.validate(d, cls.SCHEMA)
