"""AWS backup-retention detector package.

Importing this package registers the detector with the global registry via
the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.backup_retention_configured import detector  # noqa: F401
