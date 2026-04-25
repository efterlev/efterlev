"""AWS `security_group_open_ingress` detector package.

Importing this package registers the detector with the global registry
via the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.security_group_open_ingress import detector  # noqa: F401
