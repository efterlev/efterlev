"""AWS CloudTrail audit logging detector package.

Importing this package registers the detector with the global registry via
the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.cloudtrail_audit_logging import detector  # noqa: F401
