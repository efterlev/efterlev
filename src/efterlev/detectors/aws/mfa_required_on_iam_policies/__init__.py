"""AWS IAM policy MFA-required detector package.

Importing this package registers the detector with the global registry via
the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.mfa_required_on_iam_policies import detector  # noqa: F401
