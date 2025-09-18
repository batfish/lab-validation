from collections.abc import Generator, Iterator, Sequence
from copy import deepcopy
from enum import Enum
from typing import Any, ClassVar

import attr
from cerberus import Validator


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class Flow:
    """Represents a flow"""

    SCHEMA: ClassVar = {
        "src_ip": {"type": "string"},
        "dst_ip": {"type": "string"},
        "application": {"type": "string"},
    }

    src_ip: str | None = attr.ib(default=None)
    dst_ip: str
    application: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Flow":
        return Flow(**d)


class Disposition(Enum):
    """Expected flow disposition"""

    # coarse-grained flow disposition
    SUCCESS = "success"
    FAILURE = "failure"

    # fine-grained disposition - success
    ACCEPTED = "accepted"
    DELIVERED_TO_SUBNET = "delivered_to_subnet"
    EXITS_NETWORK = "exits_network"

    # fine-grained disposition - failure
    DENIED_IN = "denied_in"
    DENIED_OUT = "denied_out"
    NO_ROUTE = "no_route"
    NULL_ROUTED = "null_routed"
    NEIGHBOR_UNREACHABLE = "neighbor_unreachable"
    LOOP = "loop"
    INSUFFICIENT_INFO = "insufficient_info"

    @staticmethod
    def of(value: str) -> "Disposition":
        return Disposition[value.upper()]


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class Connectivity:
    """Contains connectivity information needed to validate Batfish traceroute for one flow."""

    SCHEMA: ClassVar = {
        "src_hostname": {"type": "string"},
        # if present, cannot be empty
        "src_location": {"type": "string", "empty": False},
        "disposition": {
            "type": "string",
            "allowed": [var.value for var in Disposition],
            "required": True,
        },
        "flow": {"type": "dict", "schema": Flow.SCHEMA, "required": True},
    }

    src_hostname: str
    src_location: str | None = attr.ib(default=None)
    disposition: Disposition
    flow: Flow

    def get_start_location(self) -> str:
        if self.src_location is not None:
            return self.src_location
        else:
            return self.src_hostname

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Connectivity":
        tmp: dict[str, Any] = deepcopy(d)
        tmp["disposition"] = Disposition.of(tmp["disposition"])
        tmp["flow"] = Flow.from_dict(tmp["flow"])
        return Connectivity(**tmp)


@attr.s(frozen=True, kw_only=True)
class ConnectivityMatrix:
    """A connectivity matrix for multiple src/dst pairs, expressed as a list of :py:class:`Connectivity` objects"""

    SCHEMA: ClassVar = {
        "entries": {
            "type": "list",
            "schema": {"type": "dict", "schema": Connectivity.SCHEMA},
            "empty": False,
        }
    }

    _entries: list[Connectivity] = attr.ib(factory=list)

    @property
    def entries(self) -> Sequence[Connectivity]:
        return self._entries

    def __iter__(self) -> Iterator[Connectivity]:
        return iter(self._entries)

    def __next__(self) -> Generator[Connectivity, None, None]:
        yield from self._entries

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ConnectivityMatrix":
        cls._validate_data(d)
        return ConnectivityMatrix(
            entries=[Connectivity.from_dict(c) for c in d["entries"]]
        )

    @classmethod
    def _validate_data(cls, d: dict[str, Any]) -> None:
        v = Validator()
        v.validate(d, cls.SCHEMA)
