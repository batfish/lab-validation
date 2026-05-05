import io
import json
import logging
import zipfile
from collections.abc import Callable, Sequence
from pathlib import Path

import attr
import pandas as pd
import pytest
from _pytest.config import Config
from pybatfish.client.session import Session
from pybatfish.datamodel.answer import TableAnswer

from lab_tests.bf_getters import (
    get_batfish_bgp_routes,
    get_batfish_evpn_routes,
    get_batfish_interfaces,
    get_batfish_main_rib_routes,
    get_vni_backed_ifaces,
)
from lab_tests.lab_getters import get_host_nos, snapshot_path
from lab_validation.validators import (
    A10AcosValidator,
    AristaValidator,
    CheckpointGaiaValidator,
    CumulusFrrValidator,
    FortiosValidator,
    IosValidator,
    IosXrValidator,
    JunosValidator,
    NxosValidator,
    PanosValidator,
    SonicValidator,
    Vendor,
)
from lab_validation.validators.batfish_models.runtime_data import SnapshotRuntimeData
from lab_validation.validators.vendor_validator import ValidationError, VendorValidator

CONNECTIVITY_FILENAME = "connectivity.yaml"
NETWORK_NAME_PREFIX = "lab_validation"
LAB_NAME_CONFIG_OPTION = "labname"

vendor_validators: dict[Vendor, Callable[[Path], VendorValidator]] = {
    Vendor.A10_ACOS: A10AcosValidator,
    Vendor.ARISTA: AristaValidator,
    Vendor.CHECKPOINTGAIA: CheckpointGaiaValidator,
    Vendor.CISCO_IOS: IosValidator,
    Vendor.CISCO_IOS_XE: IosValidator,
    Vendor.CISCO_NX: NxosValidator,
    Vendor.CISCO_XR: IosXrValidator,
    Vendor.CUMULUS: CumulusFrrValidator,
    Vendor.FORTIGATE: FortiosValidator,
    Vendor.JUNOS: JunosValidator,
    Vendor.PALOALTO: PanosValidator,
    Vendor.SONIC: SonicValidator,
}
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=logging.WARN)
logger = logging.getLogger("labvalidation")
logger.setLevel(logging.INFO)


##################
# Helper functions
##################


def is_sickbayed(
    host: str, test: str | None, test_list: Sequence[tuple[str, str]]
) -> bool:
    """
    Check if the specified host, and test are sickbayed.

    A test_list[i][1] value of `*` matches anything.
    """
    if test is None:
        return False
    for test_host, test_name in test_list:
        if (test_host == "*" or test_host == host) and (
            test_name == "*" or test_name == test
        ):
            return True
    return False


def get_vendor_validator(lab: str, host: str, vendor: Vendor) -> VendorValidator | None:
    if vendor not in vendor_validators:
        logger.warning("No validator available for vendor: %s", vendor)
        return None
    device_path = snapshot_path(lab) / "show" / host
    return vendor_validators[vendor](device_path)


def get_runtime_data(
    lab: str, validators: dict[str, VendorValidator | None]
) -> SnapshotRuntimeData:
    """Returns the runtime data for the given lab."""
    lab_nos = get_host_nos(lab)
    node_runtime_data = dict()
    for hostname, vendor in lab_nos:
        validator = validators[hostname]
        if validator is None:
            continue
        node_runtime_data[hostname] = validator.get_runtime_data()
    return SnapshotRuntimeData(runtimeData=node_runtime_data)


def init_lab(bf: Session, lab: str, validators: dict[str, VendorValidator]) -> str:
    """Initializes the given lab in the given Batfish session.

    :returns: the snapshot name
    """
    runtime_data = get_runtime_data(lab, validators)

    zipbytes = io.BytesIO()
    with zipfile.ZipFile(zipbytes, "w", zipfile.ZIP_DEFLATED) as sszip:
        # Write runtime data into zip with single top-level folder
        sszip.writestr(
            f"{lab}/batfish/runtime_data.json", json.dumps(attr.asdict(runtime_data))
        )
        # Copy configs only into zip with single top-level folder structure
        for file in snapshot_path(lab).glob("configs/**/*"):
            if file.is_file():
                # Create path within single top-level folder
                name = f"{lab}/" + str(file.relative_to(snapshot_path(lab)))
                sszip.write(file, arcname=name)
        for file in snapshot_path(lab).glob("batfish/*"):
            if file.is_file():
                name = f"{lab}/" + str(file.relative_to(snapshot_path(lab)))
                sszip.write(file, arcname=name)
        for file in snapshot_path(lab).glob("aws_configs/**/*"):
            if file.is_file():
                name = f"{lab}/" + str(file.relative_to(snapshot_path(lab)))
                sszip.write(file, arcname=name)
        for file in snapshot_path(lab).glob("sonic_configs/**/*"):
            if file.is_file():
                name = f"{lab}/" + str(file.relative_to(snapshot_path(lab)))
                sszip.write(file, arcname=name)
        for file in snapshot_path(lab).glob("hosts/**/*"):
            if file.is_file():
                name = f"{lab}/" + str(file.relative_to(snapshot_path(lab)))
                sszip.write(file, arcname=name)

    # Reset position to beginning for reading
    zipbytes.seek(0)
    bf.init_snapshot(
        zipbytes,
        name=lab,
        overwrite=True,
    )
    return lab


##########
# Fixtures
##########


@pytest.fixture(scope="module")
def bf(pytestconfig: Config):
    """Pybatfish session for OSS Batfish."""
    # Use OSS Batfish (assumes local Batfish service running on default port)
    bf = Session()
    LAB_NET_NAME = (
        f"{NETWORK_NAME_PREFIX}_{pytestconfig.getoption(LAB_NAME_CONFIG_OPTION)}"
    )

    bf.set_network(LAB_NET_NAME)
    yield bf
    # Note: OSS Batfish doesn't support delete_network, so we skip cleanup


@pytest.fixture(scope="module")
def validators(pytestconfig) -> dict[str, VendorValidator]:
    lab = pytestconfig.getoption(LAB_NAME_CONFIG_OPTION)
    lab_nos = get_host_nos(lab)
    validators = {}
    for hostname, vendor in lab_nos:
        validators[hostname] = get_vendor_validator(lab, hostname, vendor)
    return validators


@pytest.fixture(scope="module")
def snapshot(bf, pytestconfig, validators: dict[str, VendorValidator]) -> str:
    """Guarantees a lab with a given name is initialized in batfish

    :returns the snapshot name
    """
    return init_lab(bf, pytestconfig.getoption(LAB_NAME_CONFIG_OPTION), validators)


@pytest.fixture(scope="module")
def node_properties(bf, snapshot) -> pd.DataFrame:
    """Grabs node properties used in tests for the given snapshot.

    :returns the node properties answer frame.
    """
    props = {
        "Configuration_Format",
    }
    return (
        bf.q.nodeProperties(properties=",".join(props), question_name="nodep")
        .answer(snapshot=snapshot)
        .frame()
    )


@pytest.fixture(scope="module")
def interface_properties(bf, snapshot) -> TableAnswer:
    """Grabs interface properties used in tests for the given snapshot.

    :returns the interface properties answer frame.
    """
    props = {
        "Access_VLAN",
        "Active",
        "All_Prefixes",
        "Allowed_VLANs",
        "Bandwidth",
        "Description",
        "MTU",
        "Native_VLAN",
        "Speed",
        "Switchport",
        "Switchport_Mode",
        "VRF",
    }
    return bf.q.interfaceProperties(
        properties=",".join(props), question_name="intp"
    ).answer(snapshot=snapshot)


@pytest.fixture(scope="module")
def vni_ifaces(bf, snapshot, interface_properties) -> dict[str, set[str]]:
    """VLAN/IRB interface names with VNI backing per node (L2 and L3 VNIs)."""
    l2_vni_props = (
        bf.q.vxlanVniProperties(question_name="vxlan").answer(snapshot=snapshot).frame()
    )
    return get_vni_backed_ifaces(interface_properties, l2_vni_props)


@pytest.fixture(scope="module")
def ip_owners(bf, snapshot) -> pd.DataFrame:
    """Grabs IP Owners for the given snapshot.

    :returns the IP owners answer frame.
    """
    return bf.q.ipOwners(question_name="ipo").answer(snapshot=snapshot).frame()


@pytest.fixture(scope="module")
def main_rib_routes(bf, snapshot) -> pd.DataFrame:
    """Grabs Routes (main RIB) for the given snapshot.

    :returns the routes answer.
    """
    return bf.q.routes(question_name="routes").answer(snapshot=snapshot).frame()


@pytest.fixture(scope="module")
def bgp_rib_routes(bf, snapshot) -> pd.DataFrame:
    """Grabs Routes (BGP RIB) for the given snapshot.

    :returns the BGP routes answer.
    """
    return (
        bf.q.routes(rib="bgp", question_name="bgp_routes")
        .answer(snapshot=snapshot)
        .frame()
    )


@pytest.fixture(scope="module")
def evpn_rib_routes(bf, snapshot) -> pd.DataFrame:
    """Grabs Routes (EVPN RIB) for the given snapshot.

    :returns the EVPN routes answer.
    """
    return (
        bf.q.routes(rib="evpn", question_name="evpn_routes")
        .answer(snapshot=snapshot)
        .frame()
    )


################################################
# Actual tests start here.
# Parameter naming convention must be followed.
################################################


def test_configuration_format(
    hostname: str,
    vendor: Vendor,
    node_properties: pd.DataFrame,
    ip_owners: pd.DataFrame,
):
    vendor_to_cf = {
        Vendor.A10_ACOS: {"A10_ACOS"},
        Vendor.ARISTA: {"ARISTA"},
        Vendor.AWS: {"AWS"},
        Vendor.CHECKPOINTGAIA: {"CHECK_POINT_GATEWAY"},
        Vendor.CISCO_IOS: {"CISCO_IOS"},
        Vendor.CISCO_IOS_XE: {"CISCO_IOS"},
        Vendor.CISCO_NX: {"CISCO_NX"},
        Vendor.CISCO_XR: {"CISCO_IOS_XR"},
        Vendor.CUMULUS: {"CUMULUS_CONCATENATED"},
        Vendor.FORTIGATE: {"FORTIOS"},
        Vendor.JUNOS: {"FLAT_JUNIPER", "JUNIPER", "JUNIPER_SWITCH"},
        Vendor.PALOALTO: {"PALO_ALTO"},
        Vendor.SONIC: {"SONIC"},
        Vendor.UBUNTU: {"HOST"},
    }
    assert vendor in vendor_to_cf

    # Skipping test for internet node (8.8.8.8). No need to check the configuration format for internet node.
    if hostname == "8.8.8.8":
        pytest.skip(f"{hostname} represents internet")

    # During AWS data collection, ip address is being used as identifier for host.
    # so, converting ip --> hostname, E.g. 10.1.1.1 --> i-03382dae997e32485
    if vendor is Vendor.AWS:
        ipo = ip_owners[ip_owners.IP == hostname]
        hostname = ipo["Node"].values[0]

    cf_col = node_properties[
        node_properties.Node == hostname.lower()
    ].Configuration_Format

    if len(cf_col) == 0:
        raise ValidationError(
            f"Host {hostname} of vendor {vendor} is not available in batfish"
        )
    elif len(cf_col) > 1:
        raise ValidationError(
            f"Found multiple nodes with hostname {hostname} in batfish"
        )

    cf = cf_col.iloc[0]
    if cf not in vendor_to_cf[vendor]:
        raise ValidationError(
            f"Host {hostname} of vendor {vendor} has wrong Batfish configuration format {cf}"
        )


def test_interface_properties(
    snapshot: str,
    hostname: str,
    vendor: Vendor,
    interface_properties: TableAnswer,
    vni_ifaces: dict[str, set[str]],
    validators: dict[str, VendorValidator | None],
):
    validator = validators[hostname]
    if validator is None:
        pytest.skip(f"Vendor {vendor} has no validator")
        return

    batfish_interfaces = get_batfish_interfaces(interface_properties, hostname.lower())
    node_vni_ifaces = vni_ifaces.get(hostname.lower(), set())

    result = validator.validate_interface_properties(
        batfish_interfaces, node_vni_ifaces
    )
    try:
        assert result == {}
    except AssertionError as e:
        raise ValidationError from e


def test_main_rib_routes(
    snapshot: str,
    hostname: str,
    vendor: Vendor,
    main_rib_routes: pd.DataFrame,
    validators: dict[str, VendorValidator | None],
):
    validator = validators[hostname]
    if validator is None:
        pytest.skip(f"Vendor {vendor} has no validator")
        return

    batfish_routes = get_batfish_main_rib_routes(main_rib_routes, hostname.lower())

    result = validator.validate_main_rib_routes(batfish_routes)
    try:
        assert result == {}
    except AssertionError as e:
        raise ValidationError from e


def test_bgp_rib_routes(
    snapshot: str,
    hostname: str,
    vendor: Vendor,
    bgp_rib_routes: pd.DataFrame,
    validators: dict[str, VendorValidator | None],
):
    validator = validators[hostname]
    if validator is None:
        pytest.skip(f"Vendor {vendor} has no validator")
        return

    batfish_routes = get_batfish_bgp_routes(bgp_rib_routes, hostname.lower())

    result = validator.validate_bgp_rib_routes(batfish_routes)
    try:
        assert result == {}
    except AssertionError as e:
        raise ValidationError from e


def test_evpn_rib_routes(
    snapshot: str,
    hostname: str,
    vendor: Vendor,
    evpn_rib_routes: pd.DataFrame,
    validators: dict[str, VendorValidator | None],
):
    validator = validators[hostname]
    if validator is None:
        pytest.skip(f"Vendor {vendor} has no validator")
        return

    batfish_routes = get_batfish_evpn_routes(evpn_rib_routes, hostname.lower())

    result = validator.validate_evpn_rib_routes(batfish_routes)
    try:
        assert result == {}
    except AssertionError as e:
        raise ValidationError from e


# TODO: Re-enable connectivity tests when ConnectivityValidator is ported
# def test_connectivity(...):
#     pass

# def test_connectivity_matrix(...):
#     pass


def test_vi_model(bf: Session, snapshot: str) -> None:
    """Tests that the VI Model question runs successfully."""
    bf.set_snapshot(snapshot)
    bf.q.viModel().answer()


@pytest.fixture(scope="module")
def parse_warning_spec(pytestconfig: Config) -> dict | None:
    """Load parse_warnings.yaml if present."""
    import yaml

    lab = pytestconfig.getoption(LAB_NAME_CONFIG_OPTION)
    warnings_path = snapshot_path(lab) / "validation" / "parse_warnings.yaml"
    if not warnings_path.exists():
        return None
    with open(warnings_path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def host_fatal_details(
    bf: Session, snapshot: str, parse_warning_spec: dict | None
) -> dict[str, list[str]]:
    """Map hostname -> list of fatal red flag warning detail strings."""
    if parse_warning_spec is None:
        return {}

    bf.set_snapshot(snapshot)
    issues = bf.q.initIssues().answer().frame()

    fatal_rows = issues[
        (issues["Type"] == "Parse warning (redflag)")
        & (issues["Details"].str.startswith("FATAL:"))
    ]

    result: dict[str, list[str]] = {}
    for _, row in fatal_rows.iterrows():
        nodes = row.get("Nodes")
        source_lines = row.get("Source_Lines")
        if nodes:
            for node in nodes:
                result.setdefault(node, []).append(row["Details"])
        elif source_lines:
            for file_lines in source_lines:
                filename = (
                    file_lines.filename
                    if hasattr(file_lines, "filename")
                    else str(file_lines)
                )
                parts = filename.split("/")
                if len(parts) >= 2 and parts[0] == "configs":
                    result.setdefault(parts[1], []).append(row["Details"])
    return result


def test_parse_warnings(
    hostname: str,
    vendor: Vendor,
    parse_warning_spec: dict | None,
    host_fatal_details: dict[str, list[str]],
) -> None:
    """Tests that Batfish produces (or does not produce) fatal red flag warnings.

    Driven by validation/parse_warnings.yaml. Each host is tested individually
    so failures can be sickbayed per-host.
    """
    if parse_warning_spec is None:
        pytest.skip("no validation/parse_warnings.yaml")
        return

    expects_fatal = {
        e["host"]: e["contains"]
        for e in parse_warning_spec.get("expects_fatal_warning", [])
    }
    expects_no_fatal = set(parse_warning_spec.get("expects_no_fatal_warning", []))

    if hostname in expects_fatal:
        contains = expects_fatal[hostname]
        details = host_fatal_details.get(hostname, [])
        if not any(contains in d for d in details):
            raise ValidationError(
                f"expected fatal warning containing '{contains}' for '{hostname}' "
                f"but got: {details}"
            )
    elif hostname in expects_no_fatal:
        if hostname in host_fatal_details:
            raise ValidationError(
                f"unexpected fatal warning for '{hostname}': "
                f"{host_fatal_details[hostname]}"
            )
    else:
        pytest.skip(f"'{hostname}' not in parse_warnings.yaml")


# TODO: Re-enable when reachability verification logic is ported from Batfish
# def test_reachability_verifier(bf: Session, snapshot: str) -> None:
#     """Tests that the Reachability Verifier finds no bugs."""
#     bf.set_snapshot(snapshot)
#     assert_zero_results(bf.q.reachabilityVerifier().answer())
