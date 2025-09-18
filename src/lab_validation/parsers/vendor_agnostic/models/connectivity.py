import attr


@attr.s(frozen=True, auto_attribs=True)
class Connectivity:
    """Data related to real connectivity and it's result"""

    src_ip: str
    dst_ip: str
    app: str
    real_result: bool
