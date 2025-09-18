from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd
import pybatfish.datamodel.flow
import pytest

from lab_validation.parsers.vendor_agnostic.models.connectivity import Connectivity
from lab_validation.validators.ConnectivityValidator import (
    bf_disposition_converter,
    convert_bf_disposition,
    get_bf_connectivity,
    get_connectivity_files,
    get_source_ip,
    get_start_location,
    matches_disposition,
    validate_connectivity,
)
from lab_validation.validators.models.connectivity import Disposition

from .utils.common_util import MockQuestion, MockSession, MockTableAnswer

IP = "10.4.1.100"


@pytest.fixture()
def session() -> MockSession:
    return MockSession()


@pytest.fixture()
def get_ipo_answer() -> pd.DataFrame:
    data = [
        {
            "Node": "i-06286478d130ebee1",
            "VRF": "default",
            "Interface": "eni-041fed627532cc8f0",
            "IP": IP,
            "Mask": "24",
            "Active": True,
        }
    ]
    return pd.DataFrame.from_records(data)


def get_bdtr_answer_true() -> MockQuestion:
    bdtr_data = [
        {
            "Forward_Traces": [
                pybatfish.datamodel.flow.Trace(disposition="ACCEPTED", hops=[])
            ],
            "Reverse_Traces": [
                pybatfish.datamodel.flow.Trace(disposition="ACCEPTED", hops=[])
            ],
        }
    ]
    mock_bdtr_df = pd.DataFrame.from_records(bdtr_data)

    return MockQuestion(MockTableAnswer(mock_bdtr_df))


def get_bdtr_answer_false() -> MockQuestion:
    bdtr_data = [
        {
            "Forward_Traces": [
                pybatfish.datamodel.flow.Trace(disposition="NO_ROUTE", hops=[])
            ],
            "Reverse_Traces": [],
        }
    ]
    mock_bdtr_df = pd.DataFrame.from_records(bdtr_data)

    return MockQuestion(MockTableAnswer(mock_bdtr_df))


def get_bdtr_answer_false_reverse_fail() -> MockQuestion:
    bdtr_data = [
        {
            "Forward_Traces": [
                pybatfish.datamodel.flow.Trace(disposition="ACCEPTED", hops=[])
            ],
            "Reverse_Traces": [
                pybatfish.datamodel.flow.Trace(disposition="NULL_ROUTED", hops=[])
            ],
        }
    ]
    mock_bdtr_df = pd.DataFrame.from_records(bdtr_data)

    return MockQuestion(MockTableAnswer(mock_bdtr_df))


def test_success_bf_disposition_converter() -> None:
    bf_forward_disposition = "ACCEPTED"
    assert bf_disposition_converter(bf_forward_disposition)


def test_fail_bf_disposition_converter() -> None:
    bf_forward_disposition = "DENIED_IN"
    assert not bf_disposition_converter(bf_forward_disposition)


def test_bf_exception_disposition_converter() -> None:
    bf_forward_disposition = "NEW_DISPOSITION"
    with pytest.raises(Exception, match=r"Unexpected reverse disposition value"):
        bf_disposition_converter(bf_forward_disposition)


def test_valid_get_source_ip() -> None:
    src_ip = "1.1.1.1"
    result = get_source_ip(src_ip)
    assert result == "1.1.1.1"


def test_invalid_get_source_ip() -> None:
    src_ip = "1.1.1.1234"
    exc_string = f"'{src_ip}' does not appear to be an IPv4 or IPv6 address"
    with pytest.raises(ValueError) as excinfo:
        get_source_ip(src_ip)
    assert exc_string == str(excinfo.value)


def test_internet_get_start_location() -> None:
    data = [
        {
            "Node": "internet",
            "VRF": "default",
            "Interface": "out",
            "IP": "220.254.254.2",
            "Mask": "30",
            "Active": True,
        }
    ]
    ipo_row = pd.DataFrame.from_records(data)
    input_data = Connectivity(
        src_ip="8.8.8.8",
        dst_ip="10.1.1.118",
        app="icmp",
        real_result=True,
    )

    result = get_start_location(input_data, ipo_row)
    assert result == "internet"


def test_get_start_location(get_ipo_answer: pd.DataFrame) -> None:
    input_data = Connectivity(
        src_ip=IP,
        dst_ip="10.1.1.118",
        app="icmp",
        real_result=True,
    )
    result = get_start_location(input_data, get_ipo_answer)
    assert result == "i-06286478d130ebee1[eni-041fed627532cc8f0]"


def test_get_connectivity_files(tmp_path: Any) -> None:
    dummy_dir = tmp_path / IP
    dummy_dir.mkdir()
    dummy_ping_file = dummy_dir / "ping 3.95.210.72 -c 1.txt"
    dummy_ping_file.write_text("dummy ping")
    dummy_nmap_file = dummy_dir / "nmap 3.95.210.72 -p 22 -Pn.txt"
    dummy_nmap_file.write_text("dummy nmap")
    dummy_file = dummy_dir / "dummy.txt"
    dummy_file.write_text("dummy contents")

    result = get_connectivity_files(Path(dummy_dir))
    assert set(result) == set(
        [
            "ping 3.95.210.72 -c 1.txt",
            "nmap 3.95.210.72 -p 22 -Pn.txt",
        ]
    )


START_LOCATION = "i-06286478d130ebee1[eni-041fed627532cc8f0]"


def test_get_bf_connectivity(
    session: MockSession, get_ipo_answer: pd.DataFrame
) -> None:
    with patch.object(
        session.q, "bidirectionalTraceroute", create=True
    ) as bidirectionalTraceroute:
        real_data_result = Connectivity(
            src_ip=IP,
            dst_ip="10.4.1.101",
            app="icmp",
            real_result=True,
        )
        bidirectionalTraceroute.return_value = get_bdtr_answer_true()
        result = get_bf_connectivity(session, "ss", real_data_result, get_ipo_answer)

        bidirectionalTraceroute.assert_called_once_with(
            startLocation=START_LOCATION,
            headers=pybatfish.datamodel.flow.HeaderConstraints(
                srcIps=real_data_result.src_ip,
                dstIps=real_data_result.dst_ip,
                applications=real_data_result.app,
            ),
        )

        # Testing True result when we have forward and reverse flow & disposition
        assert result

        # Testing False result when we have failed reverse disposition
        bidirectionalTraceroute.return_value = get_bdtr_answer_false_reverse_fail()
        result = get_bf_connectivity(session, "ss", real_data_result, get_ipo_answer)
        assert not result

        # Testing False result when we have forward traceroute failed and reverse flow is none
        bidirectionalTraceroute.return_value = get_bdtr_answer_false()
        result = get_bf_connectivity(session, "ss", real_data_result, get_ipo_answer)
        assert not result


PING_DATA_SUCESS = """
PING 10.4.1.101 (10.4.1.101) 56(84) bytes of data.
64 bytes from 10.4.1.101: icmp_seq=1 ttl=255 time=0.015 ms

--- 10.4.1.101 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.015/0.015/0.015/0.000 ms|
"""


def test_ping_data_success_validate_connectivity(
    tmp_path: Any, session: MockSession, get_ipo_answer: pd.DataFrame
) -> None:
    with patch(
        "lab_validation.validators.ConnectivityValidator.get_bf_connectivity",
        create=True,
    ) as bf_reachability:
        dummy_dir = tmp_path / IP
        dummy_dir.mkdir()
        dummy_ping_file = dummy_dir / "ping1.txt"
        dummy_ping_file.write_text(PING_DATA_SUCESS)

        bf_reachability.return_value = True
        result = validate_connectivity(session, "ss", Path(dummy_dir), get_ipo_answer)
        real_data_result = Connectivity(
            src_ip=IP,
            dst_ip="10.4.1.101",
            app="icmp",
            real_result=True,
        )
        bf_reachability.assert_called_once_with(
            session, "ss", real_data_result, get_ipo_answer
        )
        assert result == {}

        bf_reachability.return_value = False
        result = validate_connectivity(session, "ss", Path(dummy_dir), get_ipo_answer)
        assert result == {
            Connectivity(
                src_ip="10.4.1.100",
                dst_ip="10.4.1.101",
                app="icmp",
                real_result=True,
            ): {"bf_connectivity_result": False}
        }


PING_DATA_FAIL = """
PING 10.4.1.101 (10.4.1.101) 56(84) bytes of data.

--- 10.4.1.101 ping statistics ---
2 packets transmitted, 0 received, 100% packet loss, time 1020ms|
"""


def test_diff_ping_data_fail_validate_connectivity(
    tmp_path: Any, session: MockSession, get_ipo_answer: pd.DataFrame
) -> None:
    with patch(
        "lab_validation.validators.ConnectivityValidator.get_bf_connectivity",
        create=True,
    ) as bf_connectivity:
        dummy_dir = tmp_path / IP
        dummy_dir.mkdir()
        dummy_ping_file = dummy_dir / "ping1.txt"
        dummy_ping_file.write_text(PING_DATA_FAIL)

        bf_connectivity.return_value = True
        result = validate_connectivity(session, "ss", Path(dummy_dir), get_ipo_answer)
        real_data_result = Connectivity(
            src_ip=IP,
            dst_ip="10.4.1.101",
            app="icmp",
            real_result=False,
        )
        bf_connectivity.assert_called_once_with(
            session, "ss", real_data_result, get_ipo_answer
        )
        assert result == {
            Connectivity(
                src_ip=IP,
                dst_ip="10.4.1.101",
                app="icmp",
                real_result=False,
            ): {"bf_connectivity_result": True}
        }

        bf_connectivity.return_value = False
        result = validate_connectivity(session, "ss", Path(dummy_dir), get_ipo_answer)
        assert result == {}


def test_convert_bf_disposition() -> None:
    bf_disposition = "EXITS_NETWORK"
    result = convert_bf_disposition(bf_disposition)
    assert result is Disposition.EXITS_NETWORK

    bf_disposition = "DENIED_IN"
    result = convert_bf_disposition(bf_disposition)
    assert result is Disposition.DENIED_IN


def test_matches_disposition() -> None:
    real_disposition = Disposition.SUCCESS
    bf_disposition_raw = "ACCEPTED"
    result = matches_disposition(real_disposition, bf_disposition_raw)
    assert result is True

    real_disposition = Disposition.SUCCESS
    bf_disposition_raw = "NO_ROUTE"
    result = matches_disposition(real_disposition, bf_disposition_raw)
    assert result is False

    real_disposition = Disposition.FAILURE
    bf_disposition = "NO_ROUTE"
    result = matches_disposition(real_disposition, bf_disposition)
    assert result is True

    real_disposition = Disposition.FAILURE
    bf_disposition = "ACCEPTED"
    result = matches_disposition(real_disposition, bf_disposition)
    assert result is False

    real_disposition = Disposition.ACCEPTED
    bf_disposition = "ACCEPTED"
    result = matches_disposition(real_disposition, bf_disposition)
    assert result is True

    real_disposition = Disposition.ACCEPTED
    bf_disposition = "NO_ROUTE"
    result = matches_disposition(real_disposition, bf_disposition)
    assert result is False
