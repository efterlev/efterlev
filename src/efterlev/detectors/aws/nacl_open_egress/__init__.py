"""AWS `nacl_open_egress` detector package.

Importing this package registers the detector with the global registry
via the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.nacl_open_egress import detector  # noqa: F401
