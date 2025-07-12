import re
from typing import Text

from lab_validation.parsers.vendor_agnostic.models.connectivity import Connectivity


def get_ping_result(src_ip: str, contents: str) -> Connectivity:
    """
    Reads the file contents and returns back Connectivity object
    """

    """
    # Example line for regex: "1 packets transmitted, 1 received, 0% packet loss, time 0ms"
    0 received packets indicates failure, otherwise success
    """
    result = re.search(r"packets transmitted, (\d+)( packets)? received", contents)
    if result is None:
        raise Exception("Unexpected ping result")

    received_count = int(result.groups()[0])
    success = received_count > 0
    app = "icmp"

    # Example line for regex: "PING 10.1.1.118 (10.1.1.118) 56(84) bytes of data."
    match = re.search(r"\((\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\)", contents)
    if match is None:
        raise Exception("Did not find dst_ip")
    dst_ip = match.groups()[0]

    return Connectivity(src_ip=src_ip, dst_ip=dst_ip, app=app, real_result=success)


def get_nmap_result(src_ip: str, contents: str) -> Connectivity:
    """
    Reads the file contents and returns back Connectivity object
    """
    nmap_success = ["open", "closed"]

    # Example line for regex: "22/tcp open  ssh"
    result = re.search(r"(\d+)/(tcp|udp)\s+(\S+)", contents)
    if result is None:
        raise Exception("Unexpected NMAP result")

    nmap_result = result.groups()[2]
    success = nmap_result in nmap_success
    app = f"{result.groups()[1]}/{result.groups()[0]}"

    # Example line for regex: "Nmap scan report for ip-10-2-1-205.ec2.internal (10.2.1.205)"
    match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", contents)
    if match is None:
        raise Exception("Did not find dst_ip")
    dst_ip = match.groups()[0]

    return Connectivity(src_ip=src_ip, dst_ip=dst_ip, app=app, real_result=success)


def parse_connectivity(src_ip: Text, contents: Text) -> Connectivity:
    """
    Parse vendor_agnostic file contents and returns back constructed result
    """
    if "ping statistics" in contents:
        return get_ping_result(src_ip, contents)
    elif "Nmap scan report" in contents:
        return get_nmap_result(src_ip, contents)
    else:
        raise Exception("Unexpected file")
