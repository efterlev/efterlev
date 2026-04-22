"""AWS S3 public-access-block detector package.

Importing this package registers the detector with the global registry via
the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.s3_public_access_block import detector  # noqa: F401
