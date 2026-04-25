"""AWS `s3_bucket_public_acl` detector package.

Importing this package registers the detector with the global registry
via the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.s3_bucket_public_acl import detector  # noqa: F401
