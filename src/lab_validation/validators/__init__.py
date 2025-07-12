"""Vendor-specific validator implementations."""

import enum

from .A10AcosValidator import A10AcosValidator
from .AristaValidator import AristaValidator
from .CheckpointGaiaValidator import CheckpointGaiaValidator
from .CumulusFrrValidator import CumulusFrrValidator
from .FortiosValidator import FortiosValidator
from .IosValidator import IosValidator
from .IosXrValidator import IosXrValidator
from .JunosValidator import JunosValidator
from .NxosValidator import NxosValidator
from .PanosValidator import PanosValidator
from .SonicValidator import SonicValidator


class Vendor(enum.Enum):
    """Our codes for device vendors/platforms/OSes."""

    A10_ACOS = "a10_acos"
    ARISTA = "arista"
    AWS = "aws"
    CHECKPOINTGAIA = "checkpoint_gw"
    CISCO_IOS = "ios"
    CISCO_IOS_XE = "iosxe"
    CISCO_NX = "nx"
    CISCO_XR = "iosxr"
    CUMULUS = "cumulus"
    FORTIGATE = "fortios"
    JUNOS = "junos"
    PALOALTO = "panos"
    SONIC = "sonic"
    UBUNTU = "ubuntu"

    def __str__(self) -> str:
        return str(self.value)


__all__ = [
    "A10AcosValidator",
    "AristaValidator",
    "CheckpointGaiaValidator",
    "CumulusFrrValidator",
    "FortiosValidator",
    "IosValidator",
    "IosXrValidator",
    "JunosValidator",
    "NxosValidator",
    "PanosValidator",
    "SonicValidator",
    "Vendor",
]
