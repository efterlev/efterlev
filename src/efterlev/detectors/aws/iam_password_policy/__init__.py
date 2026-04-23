"""AWS IAM account password-policy detector package.

Importing this package registers the detector with the global registry via
the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.iam_password_policy import detector  # noqa: F401
