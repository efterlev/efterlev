"""Scan primitives — parse source material and run detectors.

Importing this package also imports the scan primitive modules below, which
trigger `@primitive` registration and (transitively) `@detector`
registration via `efterlev.detectors`.
"""

from __future__ import annotations

from efterlev.primitives.scan.scan_terraform import (
    ScanTerraformInput,
    ScanTerraformOutput,
    scan_terraform,
)
from efterlev.primitives.scan.scan_terraform_plan import (
    ScanTerraformPlanInput,
    scan_terraform_plan,
)

__all__ = [
    "ScanTerraformInput",
    "ScanTerraformOutput",
    "ScanTerraformPlanInput",
    "scan_terraform",
    "scan_terraform_plan",
]
