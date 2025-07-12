from lab_validation.parsers.vendor_agnostic.commands.connectivity import (
    parse_connectivity,
)
from lab_validation.parsers.vendor_agnostic.models.connectivity import Connectivity


def test_ping_successful_parse_connectivity() -> None:
    src_ip = "10.1.1.200"
    contents = """
    PING 10.1.1.118 (10.1.1.118) 56(84) bytes of data.
64 bytes from 10.1.1.118: icmp_seq=1 ttl=255 time=0.438 ms

--- 10.1.1.118 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.438/0.438/0.438/0.000 ms|
    """

    result = parse_connectivity(src_ip, contents)
    assert result == Connectivity(
        src_ip="10.1.1.200",
        dst_ip="10.1.1.118",
        app="icmp",
        real_result=True,
    )


def test_ping_successful_osx_parse_connectivity() -> None:
    src_ip = "8.8.8.8"
    contents = """
PING 3.95.210.72 (3.95.210.72): 56 data bytes
64 bytes from 3.95.210.72: icmp_seq=0 ttl=227 time=96.354 ms

--- 3.95.210.72 ping statistics ---
1 packets transmitted, 1 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 96.354/96.354/96.354/0.000 ms|
    """

    result = parse_connectivity(src_ip, contents)
    assert result == Connectivity(
        src_ip="8.8.8.8",
        dst_ip="3.95.210.72",
        app="icmp",
        real_result=True,
    )


def test_ping_fail_parse_connectivity() -> None:
    src_ip = "10.1.1.35"
    contents = """
    PING 54.177.57.214 (54.177.57.214) 56(84) bytes of data.

--- 54.177.57.214 ping statistics ---
2 packets transmitted, 0 received, 100% packet loss, time 1022ms|
    """

    result = parse_connectivity(src_ip, contents)
    assert result == Connectivity(
        src_ip="10.1.1.35",
        dst_ip="54.177.57.214",
        app="icmp",
        real_result=False,
    )


def test_nmap_successful_parse_connectivity() -> None:
    src_ip = "10.1.1.35"
    contents = """

Starting Nmap 6.40 ( http://nmap.org ) at 2020-03-27 22:07 UTC
Nmap scan report for ip-10-2-1-205.ec2.internal (10.2.1.205)
Host is up (0.0011s latency).
PORT   STATE SERVICE
22/tcp open  ssh

Nmap done: 1 IP address (1 host up) scanned in 0.03 seconds|
    """

    result = parse_connectivity(src_ip, contents)
    assert result == Connectivity(
        src_ip="10.1.1.35",
        dst_ip="10.2.1.205",
        app="tcp/22",
        real_result=True,
    )


def test_nmap_openfiltered_parse_connectivity() -> None:
    src_ip = "10.1.1.35"
    contents = """

Starting Nmap 6.40 ( http://nmap.org ) at 2020-03-27 21:50 UTC
Nmap scan report for dns.google (10.2.2.35)
Host is up.
PORT   STATE         SERVICE
22/tcp open|filtered ssh

Nmap done: 1 IP address (1 host up) scanned in 2.03 seconds|
    """

    result = parse_connectivity(src_ip, contents)
    assert result == Connectivity(
        src_ip="10.1.1.35",
        dst_ip="10.2.2.35",
        app="tcp/22",
        real_result=False,
    )


def test_nmap_fail_parse_connectivity() -> None:
    src_ip = "10.1.1.35"
    contents = """

Starting Nmap 6.40 ( http://nmap.org ) at 2020-03-27 22:08 UTC
Nmap scan report for ip-10-1-101-28.ec2.internal (10.1.101.28)
Host is up.
PORT   STATE    SERVICE
22/tcp filtered ssh

Nmap done: 1 IP address (1 host up) scanned in 2.03 seconds|
    """

    result = parse_connectivity(src_ip, contents)
    assert result == Connectivity(
        src_ip="10.1.1.35",
        dst_ip="10.1.101.28",
        app="tcp/22",
        real_result=False,
    )
