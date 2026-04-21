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
    Literal("==[") + Word(_name_chars).set_results_name("name") + Literal("]")
)

_name = Literal("name:") + Word(_name_chars).set_results_name("name")

_mode = Literal("mode:") + Word(alphanums).set_results_name("mode")

_ip = (
    Literal("ip:")
    + Word(nums + ".").set_results_name("ip_addr")
    + Word(nums + ".").set_results_name("ip_mask")
)

_ipv6 = Literal("ipv6:") + Word(alphanums + "/" + ":").set_results_name("ipv6_addr")

_status = Literal("status:") + Word(alphanums).set_results_name("status")

_netbios_forward = Literal("netbios-forward:") + Word(alphas)

_speed_set = (
    Literal("speed:")
    + dec.set_results_name("speed")
    + Optional(Word(alphas).set_results_name("bit_rate_unit"))
    + Optional(
        Literal("(Duplex:") + Word(alphas).set_results_name("duplex") + Literal(")")
    )
)

_speed_na = Literal("speed:") + Literal("n/a")

_speed = MatchFirst([_speed_set, _speed_na])

_type = Literal("type:").suppress() + Word(alphanums).set_results_name("type")


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
