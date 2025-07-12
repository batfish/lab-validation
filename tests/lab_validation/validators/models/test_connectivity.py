import unittest
from textwrap import dedent

import yaml

from lab_validation.validators.models.connectivity import (
    Connectivity,
    ConnectivityMatrix,
    Disposition,
    Flow,
)


class ConnectivityModelTest(unittest.TestCase):
    def test_deserialization(self) -> None:
        sample = dedent(
            """
entries:
  - src_hostname: h1
    src_location: h1@vrf(foo)
    disposition: success
    flow:
      dst_ip: 10.13.13.2
      application: icmp
"""
        )
        self.assertEqual(
            ConnectivityMatrix.from_dict(yaml.safe_load(sample)),
            ConnectivityMatrix(
                entries=[
                    Connectivity(
                        src_hostname="h1",
                        src_location="h1@vrf(foo)",
                        disposition=Disposition.SUCCESS,
                        flow=Flow(dst_ip="10.13.13.2", application="icmp"),
                    )
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
