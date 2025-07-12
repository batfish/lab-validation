"""Pytest plugin that implements custom test generation for lab validation."""
from typing import List, Optional, Sequence, Tuple

import pytest

from src.lab_validation.validators import Vendor
from src.lab_validation.validators.vendor_validator import ValidationError

from .lab_getters import SNAPSHOT_PATH, get_host_nos, get_sickbay
from .sickbay import Sickbay, SickbayEntry, SkipType
from .test_labs import LAB_NAME_CONFIG_OPTION


def pytest_addoption(parser):
    """Add custom command line options to pytest. Enables us to specify a lab by name.

    See https://docs.pytest.org/en/5.4.2/reference.html#_pytest.hookspec.pytest_addoption
    """
    parser.addoption(
        f"--{LAB_NAME_CONFIG_OPTION}",
        help="The name of the lab to validate",
    )


def get_params(
    host_nos: Sequence[Tuple[str, Vendor]], sickbay: Sickbay, test_name: str
) -> List["ParameterSet"]:
    """Returns the parameterization of the given test name.

    Marks parameters for sickbayed tests as xfail, so that we see when they turn green.
    """
    parameters: List["ParameterSet"] = []
    for hostname, vendor in host_nos:
        sickbay_match: Optional[SickbayEntry] = sickbay.matches(test_name, hostname)
        if sickbay_match is None:
            # Not sickbayed
            parameters.append(pytest.param(hostname, vendor))
            continue

        # Need to sickbay this test. Figure out how and mark appropriately.
        parameters.append(
            pytest.param(
                hostname,
                vendor,
                marks=get_xfail_mark(sickbay_match),
            )
        )
    return parameters


def get_xfail_mark(bl: SickbayEntry) -> "Mark":
    reason = bl.skip.reason
    return pytest.mark.xfail(
        reason=reason if reason is not None else "This test is sickbayed",
        run=bl.skip.skip_type != SkipType.DONT_RUN,
        strict=True,
        raises=ValidationError,
    )


def pytest_generate_tests(metafunc):
    """This hook controls test generation and parameterization

    See https://docs.pytest.org/en/5.4.2/parametrize.html#pytest-generate-tests
    and https://docs.pytest.org/en/5.4.2/reference.html#_pytest.python.Metafunc
    """
    lab_name: str = metafunc.config.getoption(LAB_NAME_CONFIG_OPTION)
    if not SNAPSHOT_PATH.joinpath(lab_name).is_dir():
        raise Exception(f"snapshot '{lab_name}' is not available")
    host_nos = get_host_nos(lab_name)
    sickbay = get_sickbay(lab_name)
    func_name = metafunc.function.__name__

    # parametrize tests that require per-host validation
    if "hostname" in metafunc.fixturenames:
        metafunc.parametrize(
            "hostname,vendor",
            get_params(host_nos, sickbay, func_name),
        )


def pytest_collection_modifyitems(config, items):
    """Look at all collected tests and sickbay as needed. This applies to all not-already-parametrized tests"""
    lab_name: str = config.getoption(LAB_NAME_CONFIG_OPTION)
    sickbay = get_sickbay(lab_name)

    for item in items:
        # If this item hasn't already been marked as xfail in parameterization step
        if not list(item.iter_markers(name="xfail")):
            # if matches the sickbay
            bl_entry = sickbay.matches(item.name, None)
            if bl_entry is not None:
                item.add_marker(get_xfail_mark(bl_entry))
