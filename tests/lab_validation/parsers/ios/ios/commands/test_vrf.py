"""
Tests of the common IOS model for show vrf, using IOS show data.
"""
from lab_validation.parsers.ios.commands.vrf import parse_show_vrf
from lab_validation.parsers.ios.models.vrfs import Vrf


def test_parse_show_vrfs() -> None:
    """Test parsing show vrfs output."""
    input_text = """
    Name                             Default RD          Protocols   Interfaces
  cust10                           <not set>           ipv4        Lo10
  cust20                           <not set>           ipv4        Lo20
  """

    out = parse_show_vrf(input_text)
    assert out == [
        Vrf(
            name="cust10",
            default_rd=None,
            protocols=["ipv4"],
            interfaces=["Loopback10"],
        ),
        Vrf(
            name="cust20",
            default_rd=None,
            protocols=["ipv4"],
            interfaces=["Loopback20"],
        ),
    ]


def test_parse_show_vrfs_rd() -> None:
    """Test parsing show vrfs with route distinguishers output."""
    input_text = """
    Name                             Default RD          Protocols   Interfaces
  cust10                           1.1.2.10:10         ipv4        Lo10
  cust20                           5:10                ipv4        Lo20
  """

    out = parse_show_vrf(input_text)
    assert out == [
        Vrf(
            name="cust10",
            default_rd="1.1.2.10:10",
            protocols=["ipv4"],
            interfaces=["Loopback10"],
        ),
        Vrf(
            name="cust20",
            default_rd="5:10",
            protocols=["ipv4"],
            interfaces=["Loopback20"],
        ),
    ]


def test_parse_show_vrfs_multi_iface() -> None:
    """Test parsing multi interfaces"""
    input_text = """
Name                             Default RD            Protocols   Interfaces
  d1_ce                            65003:1               ipv4        Lo1231
                                                                     Gi1
  """

    out = parse_show_vrf(input_text)
    assert out == [
        Vrf(
            name="d1_ce",
            default_rd="65003:1",
            protocols=["ipv4"],
            interfaces=["Loopback1231", "GigabitEthernet1"],
        ),
    ]
