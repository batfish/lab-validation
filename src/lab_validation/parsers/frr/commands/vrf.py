from typing import Text

from pyparsing import Group, OneOrMore

from ..grammar.vrf import parse_vrf


def get_show_vrf(text: Text) -> dict:
    parsed_result = OneOrMore(Group(parse_vrf())).parseString(text)

    vrf_result: dict = {}
    for record in parsed_result:
        vrf_result.update({record.id: record.name})
    return vrf_result
