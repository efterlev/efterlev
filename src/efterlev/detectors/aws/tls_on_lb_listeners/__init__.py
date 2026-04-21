"""AWS LB listener TLS detector package.

Importing this package registers the detector with the global registry via
the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.tls_on_lb_listeners import detector  # noqa: F401
