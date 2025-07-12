from lab_validation.parsers.frr.grammar.vrf import parse_vrf


def test_parse_vrf() -> None:
    input_text = """
vrf internet-vrf id 11 table 1002
    """
    result = parse_vrf().parseString(input_text)
    assert result.name == "internet-vrf"
    assert result.id == "11"
    assert result.table_index == "1002"
