from pyparsing import Literal, ParserElement, Word, nums, printables


def parse_vrf() -> ParserElement:
    return (
        Literal("vrf").suppress()
        + Word(printables).set_results_name("name")
        + Literal("id").suppress()
        + Word(nums).set_results_name("id")
        + Literal("table").suppress()
        + Word(nums).set_results_name("table_index")
    )
