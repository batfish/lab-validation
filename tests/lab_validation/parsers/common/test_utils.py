from lab_validation.parsers.common.utils import loads_multi_json


def test_loads_multi_json() -> None:
    input_text = """
    {"a": 1, "b": {"c": "3"}}
    """

    results = loads_multi_json(input_text)
    assert next(results) == {"a": 1, "b": {"c": "3"}}

    input_text = """
    {"a": 1, "b": {"c": "3"}}
    {"d": 4, "e": {"f": "6"}}
    """

    results = loads_multi_json(input_text)
    assert next(results) == {"a": 1, "b": {"c": "3"}}
    assert next(results) == {"d": 4, "e": {"f": "6"}}
