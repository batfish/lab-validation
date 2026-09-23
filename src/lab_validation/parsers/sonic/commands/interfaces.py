from collections.abc import Sequence

from ..models.interfaces import SonicInterfaceStatus

_SPEED_UNITS = {"M": 1e6, "G": 1e9}


def parse_show_interfaces_status(text: str) -> Sequence[SonicInterfaceStatus]:
    """Parse SONiC 'show interfaces status'.

    Columns are located by header name. The trailing "Asym PFC" header is two
    words for one column, so it is the last header and never indexed.
    """
    lines = text.splitlines()
    header = lines[0].split()
    assert set(lines[1]) <= {"-", " "}, f"expected separator line, got {lines[1]!r}"
    col = {
        name: header.index(name)
        for name in ("Interface", "Speed", "MTU", "Oper", "Admin")
    }

    interfaces: list[SonicInterfaceStatus] = []
    for line in lines[2:]:
        fields = line.split()
        if not fields:
            continue
        interfaces.append(
            SonicInterfaceStatus(
                name=fields[col["Interface"]],
                speed=_parse_speed(fields[col["Speed"]]),
                mtu=int(fields[col["MTU"]]),
                oper_up=_parse_state(fields[col["Oper"]]),
                admin_up=_parse_state(fields[col["Admin"]]),
            )
        )
    return interfaces


def _parse_speed(speed: str) -> float:
    """Convert a speed like '40G' or '100M' to bits per second."""
    return float(speed[:-1]) * _SPEED_UNITS[speed[-1]]


def _parse_state(state: str) -> bool:
    assert state in ("up", "down"), f"unexpected interface state {state!r}"
    return state == "up"
