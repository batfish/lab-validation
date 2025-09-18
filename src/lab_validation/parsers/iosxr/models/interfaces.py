import attr


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class IosXrInterface:
    """Captures runtime properties of an interface."""

    name: str
    line_protocol: str
    admin_state: str
    prefix: str | None
    mtu: int
    # Bandwidth, in Kbps
    bw: int

    def is_physical(self) -> bool:
        virtual_prefixes = ["Loopback", "Bundle-Ether", "Null"]
        if any(self.name.startswith(p) for p in virtual_prefixes):
            return False
        if self.name.startswith("MgmtEth"):
            return False
        if "." in self.name:
            # Subinterface
            return False
        return True
