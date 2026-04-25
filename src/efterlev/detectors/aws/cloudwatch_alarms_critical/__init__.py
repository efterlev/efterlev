"""AWS `cloudwatch_alarms_critical` detector package.

Importing this package registers the detector with the global registry
via the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.cloudwatch_alarms_critical import detector  # noqa: F401
