"""AWS `guardduty_enabled` detector package.

Importing this package registers the detector with the global registry
via the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.guardduty_enabled import detector  # noqa: F401
