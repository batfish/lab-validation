from pyparsing import Literal, ParserElement, Word, nums, printables


def parse_vrf() -> ParserElement:
    return (
        Literal("vrf").suppress()
        + Word(printables).setResultsName("name")
        + Literal("id").suppress()
        + Word(nums).setResultsName("id")
        + Literal("table").suppress()
        + Word(nums).setResultsName("table_index")
    )
