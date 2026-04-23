"""Data models for lab builder."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from lab_builder.config import VendorProfile


@dataclass
class NodeInfo:
    """Information about a node discovered from containerlab inspect."""

    name: str
    kind: str
    profile: VendorProfile
    management_ip: str  # from containerlab management network
    ssh_port: int = 22
    username: str = ""
    password: str = ""

    def __post_init__(self) -> None:
        if not self.username:
            self.username = self.profile.default_username
        if not self.password:
            self.password = self.profile.default_password


@dataclass
class HealthStatus:
    """Health check result for a single node."""

    node: str
    ssh_reachable: bool = False
    bgp_established: bool | None = None  # None if BGP not configured
    ospf_full: bool | None = None
    isis_up: bool | None = None
    platform_warnings: list[str] = field(default_factory=list)
    details: str = ""

    @property
    def healthy(self) -> bool:
        if not self.ssh_reachable:
            return False
        if self.platform_warnings:
            return False
        for status in [self.bgp_established, self.ospf_full, self.isis_up]:
            if status is False:
                return False
        return True


@dataclass
class CollectedData:
    """Results of show command collection for a node."""

    node: str
    output_dir: Path
    files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
