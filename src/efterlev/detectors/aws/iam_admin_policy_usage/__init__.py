"""AWS `iam_admin_policy_usage` detector package.

Importing this package registers the detector with the global registry
via the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.iam_admin_policy_usage import detector  # noqa: F401
