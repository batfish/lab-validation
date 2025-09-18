import attr


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class CheckpointInterface:
    """Captures runtime properties of an interface."""

    name: str
    state: bool
    type: str
    # TODO Worth parsing link-state? When is link-state different from overall state?
    mtu: int
    # Speed in bits/sec
    speed: int | None
    prefix: str | None
