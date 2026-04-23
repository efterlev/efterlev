"""AWS CloudTrail log-file-validation detector package.

Importing this package registers the detector with the global registry via
the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.cloudtrail_log_file_validation import detector  # noqa: F401
