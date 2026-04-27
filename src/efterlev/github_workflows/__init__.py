"""GitHub Actions workflow source — repo-metadata detector input (Priority 1.2).

Workflows live at `.github/workflows/*.yml` in the repo. Detectors with
`source="github-workflows"` receive a list of `WorkflowFile` records from
the `scan_github_workflows` primitive — analogous to how Terraform-source
detectors receive `TerraformResource` records from `scan_terraform`.

Public API:
- `WorkflowFile` (Pydantic model): one parsed workflow file
- `parse_workflow_tree(target_dir)`: walk `.github/workflows/` and parse all .yml/.yaml
- `parse_workflow_file(path)`: parse a single file (used by tests + helpers)
- `WorkflowParseResult`: collect-and-continue result type, mirrors `TerraformParseResult`
"""

from __future__ import annotations

from efterlev.github_workflows.parser import (
    WorkflowFile,
    WorkflowParseResult,
    parse_workflow_file,
    parse_workflow_tree,
)

__all__ = [
    "WorkflowFile",
    "WorkflowParseResult",
    "parse_workflow_file",
    "parse_workflow_tree",
]
