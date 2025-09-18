from lab_validation.parsers.fortios.commands.interfaces import (
    parse_get_system_interface,
    parse_get_system_interface_physical,
)
from lab_validation.parsers.fortios.models.interfaces import (
    FortiosInterface,
    FortiosPhysicalInterface,
)


def test_parse_record_physical() -> None:
    # Partly from https://docs.fortinet.com/document/fortigate/6.0.0/cli-reference/790821/system-interface-physical
    input_text = """
== [onboard]
    ==[port1]
        mode: static
        ip: 192.168.122.2 255.255.255.0
        ipv6: ::/0
        status: up
        speed: 10000Mbps (Duplex: full)
    ==[test]
        mode: static
        ip: 192.168.123.2 255.255.255.0
        ipv6: ::/0
        status: up
        speed: 100
    ==[port3]
        mode: static
        status: down
        speed: n/a
    """
    interfaces = parse_get_system_interface_physical(input_text)
    assert interfaces == [
        FortiosPhysicalInterface(
            name="port1",
            mode="static",
            ip_addr="192.168.122.2",
            ip_mask="255.255.255.0",
            ipv6_addr="::/0",
            status="up",
            speed=10000,
            bit_rate_unit="Mbps",
            duplex="full",
        ),
        FortiosPhysicalInterface(
            name="test",
            mode="static",
            ip_addr="192.168.123.2",
            ip_mask="255.255.255.0",
            ipv6_addr="::/0",
            status="up",
            speed=100,
            bit_rate_unit=None,
            duplex=None,
        ),
        FortiosPhysicalInterface(
            name="port3",
            mode="static",
            ip_addr=None,
            ip_mask=None,
            ipv6_addr=None,
            status="down",
            speed=None,
            bit_rate_unit=None,
            duplex=None,
        ),
    ]


def test_parse_record_physical_empty(caplog) -> None:
    input_text = """
== [onboard]
    """
    interfaces = parse_get_system_interface_physical(input_text)
    assert not interfaces
    assert "No physical interface data found" in caplog.text


def test_parse_record() -> None:
    input_text = """
== [ port10 ]
name: port10   mode: static    ip: 0.0.0.0 0.0.0.0   status: up    netbios-forward: disable    type: physical   ring-rx: 0   ring-tx: 0   netflow-sampler: disable    sflow-sampler: disable    src-check: enable    explicit-web-proxy: disable    explicit-ftp-proxy: disable    proxy-captive-portal: disable    mtu-override: disable    wccp: disable    drop-overlapped-fragment: disable    drop-fragment: disable
== [ ssl.root ]
name: ssl.root   ip: 0.0.0.0 0.0.0.0   status: up    netbios-forward: disable    type: tunnel   netflow-sampler: disable    sflow-sampler: disable    src-check: enable    explicit-web-proxy: disable    explicit-ftp-proxy: disable    proxy-captive-portal: disable    wccp: disable
== [ fortilink ]
name: fortilink   mode: static    ip: 169.254.1.1 255.255.255.0   status: up    netbios-forward: disable    type: aggregate   netflow-sampler: disable    sflow-sampler: disable    src-check: enable    explicit-web-proxy: disable    explicit-ftp-proxy: disable    proxy-captive-portal: disable    mtu-override: disable    wccp: disable    drop-overlapped-fragment: disable    drop-fragment: disable
== [ loopback123 ]
name: loopback123   ip: 192.168.123.2 255.255.255.255   status: up    type: loopback   netflow-sampler: disable    sflow-sampler: disable    src-check: enable    explicit-web-proxy: disable    explicit-ftp-proxy: disable    proxy-captive-portal: disable
    """
    interfaces = parse_get_system_interface(input_text)
    assert interfaces == [
        FortiosInterface(
            name="port10",
            mode="static",
            ip_addr="0.0.0.0",
            ip_mask="0.0.0.0",
            status="up",
            type="physical",
        ),
        FortiosInterface(
            name="ssl.root",
            mode=None,
            ip_addr="0.0.0.0",
            ip_mask="0.0.0.0",
            status="up",
            type="tunnel",
        ),
        FortiosInterface(
            name="fortilink",
            mode="static",
            ip_addr="169.254.1.1",
            ip_mask="255.255.255.0",
            status="up",
            type="aggregate",
        ),
        FortiosInterface(
            name="loopback123",
            ip_addr="192.168.123.2",
            ip_mask="255.255.255.255",
            mode=None,
            status="up",
            type="loopback",
        ),
    ]


def test_parse_record_empty(caplog) -> None:
    input_text = ""
    interfaces = parse_get_system_interface(input_text)
    assert not interfaces
    assert "No interface data found" in caplog.text
