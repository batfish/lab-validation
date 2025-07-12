from pathlib import Path

from lab_validation.validators.batfish_models.runtime_data import NodeRuntimeData

from .vendor_validator import VendorValidator


class SonicValidator(VendorValidator):
    def __init__(self, device_path: Path) -> None:
        self.device_path: Path = device_path

    def get_runtime_data(self) -> NodeRuntimeData:
        """Currently produces empty NodeRuntimeData. Pending show interfaces"""
        return NodeRuntimeData()
