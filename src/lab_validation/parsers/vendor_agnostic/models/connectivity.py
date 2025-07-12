from typing import Text

import attr


@attr.s(frozen=True, auto_attribs=True)
class Connectivity(object):
    """Data related to real connectivity and it's result"""

    src_ip: Text
    dst_ip: Text
    app: Text
    real_result: bool
