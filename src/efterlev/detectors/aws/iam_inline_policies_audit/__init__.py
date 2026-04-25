"""AWS `iam_inline_policies_audit` detector package.

Importing this package registers the detector with the global registry
via the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.iam_inline_policies_audit import detector  # noqa: F401
