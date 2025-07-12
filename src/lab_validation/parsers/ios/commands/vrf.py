from typing import Sequence, Text

from ttp import ttp

from ...common.utils import convert_cisco_intf_name
from ..models.vrfs import Vrf


def parse_show_vrf(vrf_output: Text) -> Sequence[Vrf]:
    """Parses show vrf output for IOS or IOS_XE"""
    if not vrf_output.strip():
        # IOS/XE output will be empty if there are no non-default vrfs
        return []
    vrfs = []

    show_vrf_obj = ttp(data=vrf_output, template=get_vrf_templated())
    show_vrf_obj.parse()

    # Record fields for the current VRF we are processing
    curr_name = ""
    curr_interfaces = []

    # Index note: 1st index is for group name and 2nd index is for data of that group. See Example here for reference
    # https://ttp.readthedocs.io/en/latest/Match%20Variables/index.html
    for record in show_vrf_obj.result()[0][0]:
        name = record["Name"]
        if name == "":
            curr_interfaces.append(_append_iface(record))
            continue

        # We have name, which means a (new) VRF
        assert curr_name != name

        # We have reached the end of previous VRF, finalize it.
        curr_name = name
        curr_default_rd = (
            record["Default_RD"] if record["Default_RD"] != "<not set>" else None
        )
        curr_protocols = list(record["Protocols"].split(","))
        curr_interfaces = []
        iface = record.get("Interfaces")
        if iface != "":
            curr_interfaces.append(convert_cisco_intf_name(iface))
        # else: just means a VRF with no interfaces; OK in this case, nothing to do
        vrfs.append(
            Vrf(
                name=curr_name,
                default_rd=curr_default_rd,
                protocols=curr_protocols,
                interfaces=curr_interfaces,
            )
        )
    return vrfs


def get_vrf_templated() -> Text:
    """Return the template for show_vrf"""

    template = """
<group>
Name                             Default_RD            Protocols   Interfaces   {{ _headers_ }}
</group>
"""
    return template


def _append_iface(record: dict) -> Text:
    if record.get("Interfaces") == "":
        raise Exception(f'Interface value "" is not expected in this record: {record}')
    return convert_cisco_intf_name(record["Interfaces"])
