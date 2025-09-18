import json
from pathlib import Path
from typing import Sequence, Tuple

import yaml

from lab_validation.validators import Vendor

from .sickbay import Sickbay

# Find snapshots directory relative to this file's location
_this_file = Path(__file__).resolve()  # Make sure path is absolute
_lab_tests_dir = _this_file.parent
_project_root = _lab_tests_dir.parent
SNAPSHOT_PATH = _project_root / "snapshots"
SHOW_DATA_PATH = "show"
SICKBAY_FILE = "sickbay.yaml"
HOST_NOS_FILE = "host_nos.txt"
CONNECTIVITY_MATRIX_FILE = "connectivity.yaml"


def snapshot_path(lab_name: str) -> Path:
    return SNAPSHOT_PATH.joinpath(lab_name)


def get_host_nos(lab_name: str) -> Sequence[Tuple[str, Vendor]]:
    """Returns a list of tuples (hostname, vendor) for the named lab.

    Read host and network OS from specified file.
    File should be in the format [(hostname1, vendor_format_string1), (host2, vfs2), ...]
    """
    nos_path = snapshot_path(lab_name) / SHOW_DATA_PATH / HOST_NOS_FILE
    assert nos_path.is_file()
    nos_data = json.loads(nos_path.read_text())
    return list((i, Vendor(j)) for i, j in nos_data.items())


def get_sickbay(lab_name: str) -> Sickbay:
    """
    Get the test Sickbay, specifying which tests, and hosts to skip per lab.

    See Sickbay schema for how to write a sickbay file. Here we expect a YAML version
    """
    sickbay_path = Path(snapshot_path(lab_name), "validation", SICKBAY_FILE)
    if sickbay_path.is_file():
        with open(sickbay_path) as f:
            return Sickbay.from_dict(yaml.safe_load(f))
    return Sickbay(entries=[])


def get_connectivity_matrix(lab_name: str):  # -> Optional[ConnectivityMatrix]:
    # TODO: Implement connectivity matrix when needed
    return None
