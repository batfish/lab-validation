from lab_validation.parsers.frr.commands.interfaces import parse_show_interface
from lab_validation.parsers.frr.models.interfaces import FrrInterface


def test_parse_record() -> None:
    input_text = """
Interface swp1 is up, line protocol is up
  Link ups:       0    last: (never)
  Link downs:     0    last: (never)
  PTM status: disabled
  vrf: default
  index 3 metric 0 mtu 1500 speed 1000
  flags: <UP,BROADCAST,RUNNING,MULTICAST>
  Type: Ethernet
  HWaddr: 08:00:27:01:7a:c6
  inet 10.127.0.1/31
  inet6 fe80::a00:27ff:fe01:7ac6/64
  Interface Type Other
    """
    interfaces = parse_show_interface(input_text)
    assert interfaces == [
        FrrInterface(
            name="swp1",
            admin=True,
            line=True,
            mtu=1500,
            bandwidth=1000000000,
        )
    ]


def test_parse_multi_record() -> None:
    input_text = """
Interface swp1 is up, line protocol is up
  Link ups:       0    last: (never)
  Link downs:     0    last: (never)
  PTM status: disabled
  vrf: default
  index 3 metric 0 mtu 1500 speed 1000
  flags: <UP,BROADCAST,RUNNING,MULTICAST>
  Type: Ethernet
  HWaddr: 08:00:27:01:7a:c6
  inet 10.127.0.1/31
  inet6 fe80::a00:27ff:fe01:7ac6/64
  Interface Type Other

Interface swp6 is down
  Link ups:       1    last: 2020/01/21 19:12:05.78
  Link downs:     6    last: 2020/01/22 01:46:14.67
  PTM status: disabled
  vrf: default
  index 8 metric 0 mtu 1500 speed 1000
  flags: <BROADCAST,PROMISC,MULTICAST>
  Type: Ethernet
  HWaddr: 08:00:27:a9:5f:fe
  Interface Type Other
    """
    interfaces = parse_show_interface(input_text)
    assert interfaces == [
        FrrInterface(
            name="swp1",
            admin=True,
            line=True,
            mtu=1500,
            bandwidth=1000000000,
        ),
        FrrInterface(
            name="swp6",
            admin=False,
            line=False,
            mtu=1500,
            bandwidth=1000000000,
        ),
    ]


def test_parse_record_user_defined_bandwidth() -> None:
    input_text = """
Interface swp1 is up, line protocol is up
  Link ups:       0    last: (never)
  Link downs:     0    last: (never)
  PTM status: disabled
  vrf: default
  index 3 metric 0 mtu 1500 speed 1000
  flags: <UP,BROADCAST,RUNNING,MULTICAST>
  Type: Ethernet
  HWaddr: 08:00:27:0f:c3:1c
  bandwidth 1 Mbps
  inet 10.127.0.9/31
  inet6 fe80::a00:27ff:fe0f:c31c/64
  Interface Type Other
    """
    interfaces = parse_show_interface(input_text)
    assert interfaces == [
        FrrInterface(
            name="swp1",
            admin=True,
            line=True,
            mtu=1500,
            bandwidth=1000000,
        )
    ]
