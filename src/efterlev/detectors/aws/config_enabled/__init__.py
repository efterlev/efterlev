"""AWS `config_enabled` detector package.

Importing this package registers the detector with the global registry
via the `@detector` decorator in `detector.py`.
"""

from __future__ import annotations

from efterlev.detectors.aws.config_enabled import detector  # noqa: F401
