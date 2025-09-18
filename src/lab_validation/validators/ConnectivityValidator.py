import ipaddress
import os
from collections.abc import Sequence
from os import PathLike, path
from typing import Any

import pandas as pd
from pybatfish.client.session import Session
from pybatfish.datamodel import HeaderConstraints

from lab_validation.parsers.vendor_agnostic.commands.connectivity import (
    parse_connectivity,
)
from lab_validation.parsers.vendor_agnostic.models.connectivity import Connectivity
from lab_validation.validators.models.connectivity import (
    Connectivity as ConnectivityMatrix_Connectivity,
    ConnectivityMatrix,
    Disposition,
    Flow,
)

DISPOSITION_SUCCESS = ["ACCEPTED", "DELIVERED_TO_SUBNET", "EXITS_NETWORK"]
DISPOSITION_FAIL = [
    "DENIED_IN",
    "DENIED_OUT",
    "NO_ROUTE",
    "NULL_ROUTED",
    "NEIGHBOR_UNREACHABLE",
    "LOOP",
    "INSUFFICIENT_INFO",
]


def validate_connectivity(
    bf: Session, snapshot: str, device_path: PathLike, ipo_row: pd.DataFrame
) -> dict[Any, Any]:
    """
    Validate Batfish connectivity results & return diff that do not match with real data
    :param bf: Batfish session
    :param device_path: path to the connectivity data for a device. Path has to end with directory name which will
        represent source ip
    :param ipo_row: ipowner row for a given host
    :return: diff of real_data & Batfish connectivity that do not match
    """
    connectivity_files = get_connectivity_files(device_path)
    diff = {}
    for filename in connectivity_files:
        try:
            # AWS: Parent dir of device in show data is the source ip. e.g. show --> 10.1.1.1
            src_ip = get_source_ip(os.path.basename(device_path))
        except ValueError:
            # GNS3 ubuntu: source ip is available in filename e.g. 'ping_-c_1_-S_192.168.123.1_192.168.123.1.txt'
            src_ip = get_source_ip(filename.split("_")[4])

        with open(path.join(device_path, filename)) as f:
            contents = f.read()

        real_data_result = parse_connectivity(src_ip, contents)
        bf_result = get_bf_connectivity(bf, snapshot, real_data_result, ipo_row)

        if real_data_result.real_result != bf_result:
            diff[real_data_result] = {"bf_connectivity_result": bf_result}

    return diff


def get_bf_connectivity(
    bf: Session, snapshot: str, real_data_result: Connectivity, ipo_row: pd.DataFrame
) -> bool:
    """
    :param bf: Batfish session
    :param snapshot: the snapshot
    :param real_data_result: parsed result from real data connectivity files
    :param ipo_row: ipowner row for a given host
    :return: Batfish connectivity result. `True` denotes connectivity is successful otherwise it is failed.
    """
    sl = get_start_location(real_data_result, ipo_row)

    tr_output = (
        bf.q.bidirectionalTraceroute(  # type: ignore
            startLocation=sl,
            headers=HeaderConstraints(
                srcIps=real_data_result.src_ip,
                dstIps=real_data_result.dst_ip,
                applications=real_data_result.app,
            ),
        )
        .answer(snapshot=snapshot)
        .frame()
    )

    # Successful reverse flow implies forward flow succeeded
    # Note: ECMP(multiple traces) are not being checked for now, will add support later when required
    if len(tr_output.Reverse_Traces[0]) == 0:
        return False
    return bf_disposition_converter(tr_output.Reverse_Traces[0][0].disposition)


def get_connectivity_files(device_path: PathLike) -> Sequence[str]:
    files = next(os.walk(str(device_path)))[2]
    return [i for i in files if i.startswith("ping") or i.startswith("nmap")]


def get_source_ip(src_ip: str) -> str:
    assert ipaddress.ip_address(src_ip)
    return src_ip


def get_start_location(input_data: Connectivity, ipo_row: pd.DataFrame) -> str:
    # source ip '8.8.8.8' represents node on internet.
    if input_data.src_ip == "8.8.8.8":
        return "internet"
    else:
        node_name = ipo_row["Node"].values[0]
        interface = ipo_row["Interface"].values[0]
        return f"{node_name}[{interface}]"


def bf_disposition_converter(bf_reverse_disposition: str) -> bool:
    if bf_reverse_disposition in DISPOSITION_SUCCESS:
        return True
    elif bf_reverse_disposition in DISPOSITION_FAIL:
        return False
    else:
        raise Exception("Unexpected reverse disposition value")


def validate_connectivity_matrix(
    bf: Session, snapshot: str, matrix: ConnectivityMatrix
) -> dict[Flow, str]:
    # Keep track of all differences found:
    differences: dict[Flow, str] = {}
    for conn_entry in matrix:
        tr_output = (
            bf.q.bidirectionalTraceroute(  # type: ignore
                startLocation=conn_entry.get_start_location(),
                headers=HeaderConstraints(
                    srcIps=conn_entry.flow.src_ip,
                    dstIps=conn_entry.flow.dst_ip,
                    applications=conn_entry.flow.application,
                ),
            )
            .answer(snapshot=snapshot)
            .frame()
        )

        # Note: ECMP(multiple traces) are not being checked for now, will add support later when required
        # Check reverse trace is successful
        if len(tr_output.Reverse_Traces[0]) != 0:
            get_traceroute_diff(
                conn_entry, tr_output.Reverse_Traces[0][0].disposition, differences
            )
        # Check forward trace is successful
        elif len(tr_output.Forward_Traces[0]) != 0:
            get_traceroute_diff(
                conn_entry, tr_output.Forward_Traces[0][0].disposition, differences
            )
        else:
            raise ValueError("Batfish traceroute failed")

    return differences


def get_traceroute_diff(
    real_entry: ConnectivityMatrix_Connectivity,
    bf_disposition_raw: str,
    differences: dict[Flow, str],
) -> None:
    """Get traceroute diff"""
    traceroute_match = matches_disposition(real_entry.disposition, bf_disposition_raw)
    if traceroute_match is False:
        differences[real_entry.flow] = (
            f"Real: {real_entry.disposition.value}, Batfish: {bf_disposition_raw}"
        )


def matches_disposition(real_disposition: Disposition, bf_disposition_raw: str) -> bool:
    """Match real vs batfish traceroute disposition"""
    bf_disposition = convert_bf_disposition(bf_disposition_raw)
    if real_disposition == Disposition.SUCCESS:
        return bf_disposition.value.upper() in DISPOSITION_SUCCESS
    elif real_disposition == Disposition.FAILURE:
        return bf_disposition.value.upper() in DISPOSITION_FAIL
    else:
        return real_disposition == bf_disposition


def convert_bf_disposition(bf_disposition_raw: str) -> Disposition:
    """
    Convert batfish disposition string to object `Disposition`
    """
    if (
        bf_disposition_raw in DISPOSITION_SUCCESS
        or bf_disposition_raw in DISPOSITION_FAIL
    ):
        return Disposition.of(bf_disposition_raw)
    else:
        raise ValueError("Unexpected batfish disposition value")
