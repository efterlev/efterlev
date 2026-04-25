"""AWS `iam_service_account_keys_age` detector package.

Importing this package registers the detector with the global registry
via the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.iam_service_account_keys_age import detector  # noqa: F401
