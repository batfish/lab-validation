from pyparsing import (
    Combine,
    Literal,
    MatchFirst,
    Optional,
    ParserElement,
    SkipTo,
    Word,
    oneOf,
    printables,
    stringEnd,
)

from lab_validation.parsers.common.tokens import dec, to_eol

_state = MatchFirst([Literal("up"), Literal("down")])


def interface_block() -> ParserElement:
    iface_line = _get_iface_line()
    return (
        iface_line
        + Optional(_get_admin_line())
        + SkipTo("MTU")
        + _get_mtu_bw_line()
        + SkipTo("Encapsulation")
        + to_eol
        + Optional(_get_port_mode_line())
        + SkipTo(MatchFirst([iface_line, stringEnd]))
    )


def _get_iface_line() -> ParserElement:
    port_status_reason = [
        "(Administratively down)",  # iface is admin down
        "(VLAN/BD is down)",  # iface does not have any active members
        "(VLAN/BD does not exist)",  # the vlan has not been declared via a top level vlan N statement
        "(Link not connected)",  # Physical cable is not connected
        "(SFP not inserted)",  # SFP module is not connected in SFP port
    ]
    return (
        Combine(
            oneOf(["Ethernet", "loopback", "mgmt", "port-channel", "vasi", "Vlan"])
            + Word(printables)
        ).set_results_name("name")
        + "is"
        + Optional(
            _state.set_results_name("admin_state")
            + Optional(
                MatchFirst(
                    [Literal(reason) for reason in port_status_reason]
                ).set_results_name("port_status_reason")
            )
            + ", line protocol is"
        )
        + _state.set_results_name("line_state")
        + Optional(
            MatchFirst(
                [Literal(reason) for reason in port_status_reason]
            ).set_results_name("port_status_reason")
        )
        + to_eol
    )


def _get_admin_line() -> ParserElement:
    return "admin state is" + _state.set_results_name("admin_state") + to_eol


def _get_mtu_bw_line() -> ParserElement:
    return (
        "MTU"
        + dec.set_results_name("mtu")
        + "bytes,"
        + "BW"
        + dec.set_results_name("bw")
        + "Kbit,"
        + to_eol
    )


def _get_port_mode_line() -> ParserElement:
    return "Port mode is" + Word(printables).set_results_name("mode") + to_eol
