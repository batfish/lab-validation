# coding: utf-8
"""Contains helper pyparsing tokens that can be shared across parsers."""
from pyparsing import Combine, MatchFirst, Regex, White, pyparsing_common, restOfLine

ip = pyparsing_common.ipv4_address
prefix_length = MatchFirst([Regex(r"3[0-2]"), Regex(r"[12][0-9]"), Regex(r"[0-9]")])
prefix = Combine(ip + "/" + prefix_length)
dec = pyparsing_common.integer
route_distinguisher = Combine(ip + ":" + dec) | Combine(dec + ":" + dec)
to_eol = restOfLine
newline = White("\r\n")
uptime = dec + ":" + dec + ":" + dec


def printables_and_space(length: int) -> Regex:
    """
    Creates a Regex pattern that matches printables + space for exact length.

    This replaces the deprecated Word(printables + " ", exact=N) pattern that
    no longer works in newer pyparsing versions due to missing re_match attribute.

    Args:
        length: Exact number of characters to match

    Returns:
        Regex pattern matching printables + space for the specified length
    """
    return Regex(r"[0-9a-zA-Z!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~ ]" + f"{{{length}}}")
