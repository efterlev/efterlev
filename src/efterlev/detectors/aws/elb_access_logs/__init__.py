"""AWS `elb_access_logs` detector package.

Importing this package registers the detector with the global registry
via the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.elb_access_logs import detector  # noqa: F401
