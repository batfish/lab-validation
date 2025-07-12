import re
from typing import Text, Tuple


def remove_unused_lines(text: Text) -> Text:
    """
    remove "{master:0}" at the end to make the text a valid json string
    """
    match = re.fullmatch(r"(?P<json_text>.*){master:0}.*", text, re.DOTALL)

    if match is None:
        return text
    else:
        return match["json_text"]


# Table header includes optional VRF name and RIB
_table_header = re.compile(r"((?P<vrf>.*)\.)?(?P<rib>inet6?\.0)")


def _parse_table_header(vrf_ip_info: Text) -> Tuple[Text, Text]:
    m = _table_header.fullmatch(vrf_ip_info)
    assert m is not None
    vrf = m.group("vrf") if m.group("vrf") else "default"
    rib = m.group("rib")
    return vrf, rib
