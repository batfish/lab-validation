from lab_validation.parsers.frr.commands.vrf import get_show_vrf


def test_get_show_vrf() -> None:
    input_text = """
vrf internet-vrf id 11 table 1002
vrf mgmt id 9 table 1001
    """
    result = get_show_vrf(input_text)

    assert result["11"] == "internet-vrf"
    assert result["9"] == "mgmt"
