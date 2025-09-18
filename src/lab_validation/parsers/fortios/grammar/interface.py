from pyparsing import (
    Literal,
    MatchFirst,
    Optional,
    ParserElement,
    Word,
    alphanums,
    alphas,
    nums,
)

from ...common.tokens import dec, to_eol

# Assume names will be simple, e.g. no special chars like `[]`
_name_chars = alphanums + "."

_iface_line = Literal("==") + Literal("[") + Word(_name_chars) + Literal("]")

_physical_iface_line = (
    Literal("==[") + Word(_name_chars).setResultsName("name") + Literal("]")
)

_name = Literal("name:") + Word(_name_chars).setResultsName("name")

_mode = Literal("mode:") + Word(alphanums).setResultsName("mode")

_ip = (
    Literal("ip:")
    + Word(nums + ".").setResultsName("ip_addr")
    + Word(nums + ".").setResultsName("ip_mask")
)

_ipv6 = Literal("ipv6:") + Word(alphanums + "/" + ":").setResultsName("ipv6_addr")

_status = Literal("status:") + Word(alphanums).setResultsName("status")

_netbios_forward = Literal("netbios-forward:") + Word(alphas)

_speed_set = (
    Literal("speed:")
    + dec.setResultsName("speed")
    + Optional(Word(alphas).setResultsName("bit_rate_unit"))
    + Optional(
        Literal("(Duplex:") + Word(alphas).setResultsName("duplex") + Literal(")")
    )
)

_speed_na = Literal("speed:") + Literal("n/a")

_speed = MatchFirst([_speed_set, _speed_na])

_type = Literal("type:").suppress() + Word(alphanums).setResultsName("type")


def interface_block() -> ParserElement:
    """Parse interface block from `get system interface` output."""
    return (
        _iface_line
        + _name
        + Optional(_mode)
        + Optional(_ip)
        + _status
        + Optional(_netbios_forward)
        + _type
        + to_eol
    )


def physical_interface_block() -> ParserElement:
    """Parse interface block from `get system interface physical` output."""
    return _physical_iface_line + _mode + Optional(_ip + _ipv6) + _status + _speed
