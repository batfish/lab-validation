from lab_validation.parsers.junos.grammar.utils import rib_meta_info


def test_table_header() -> None:
    parsed_data = rib_meta_info().parseString(
        """vrf.inet.0: 21 destinations, 21 routes (21 active, 0 holddown, 0 hidden)
        + = Active Route, - = Last Active, * = Both
        """
    )
    assert parsed_data.vrf_ip_info == "vrf.inet.0"
