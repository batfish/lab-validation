import pytest

from lab_validation.parsers.sonic.commands.interfaces import (
    parse_show_interfaces_status,
)
from lab_validation.parsers.sonic.models.interfaces import SonicInterfaceStatus

# Real output from a containerlab sonic-vm node (SONiC.202605), first and
# last rows.
SHOW_INTERFACES_STATUS = """\
  Interface            Lanes    Speed    MTU    FEC           Alias    Vlan    Oper    Admin    Type    Asym PFC
-----------  ---------------  -------  -----  -----  --------------  ------  ------  -------  ------  ----------
  Ethernet0      25,26,27,28      40G   9100    N/A    fortyGigE0/0  routed      up       up     N/A         N/A
Ethernet124     97,98,99,100      40G   9100    N/A  fortyGigE0/124  routed    down       up     N/A         N/A
"""  # noqa: E501


def test_parse_show_interfaces_status() -> None:
    assert parse_show_interfaces_status(SHOW_INTERFACES_STATUS) == [
        SonicInterfaceStatus(
            name="Ethernet0", speed=40e9, mtu=9100, oper_up=True, admin_up=True
        ),
        SonicInterfaceStatus(
            name="Ethernet124", speed=40e9, mtu=9100, oper_up=False, admin_up=True
        ),
    ]


def test_parse_show_interfaces_status_megabit_speed() -> None:
    text = SHOW_INTERFACES_STATUS.replace("40G   9100", "100M   9100", 1)
    assert parse_show_interfaces_status(text)[0].speed == 100e6


def test_parse_show_interfaces_status_rejects_unknown_state() -> None:
    text = SHOW_INTERFACES_STATUS.replace("up       up", "up  unknown", 1)
    with pytest.raises(AssertionError):
        parse_show_interfaces_status(text)
