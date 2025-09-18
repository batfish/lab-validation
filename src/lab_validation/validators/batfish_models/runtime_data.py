"""Runtime data models for Batfish."""

from typing import Optional

import attr


@attr.s(frozen=True)
class InterfaceRuntimeData:
    """Interface runtime data corresponding to Batfish InterfaceRuntimeData."""

    bandwidth = attr.ib(type=Optional[float], default=None, kw_only=True)
    lineUp = attr.ib(type=Optional[bool], default=None, kw_only=True)
    speed = attr.ib(type=Optional[float], default=None, kw_only=True)


@attr.s(frozen=True)
class NodeRuntimeData:
    """Node runtime data corresponding to Batfish RuntimeData."""

    interfaces = attr.ib(
        type=dict[str, InterfaceRuntimeData], factory=dict, kw_only=True
    )


@attr.s(frozen=True)
class SnapshotRuntimeData:
    """Snapshot runtime data corresponding to Batfish SnapshotRuntimeData."""

    runtimeData = attr.ib(type=dict[str, NodeRuntimeData], factory=dict, kw_only=True)
