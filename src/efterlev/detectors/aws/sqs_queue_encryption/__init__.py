"""AWS `sqs_queue_encryption` detector package.

Importing this package registers the detector with the global registry
via the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.sqs_queue_encryption import detector  # noqa: F401
