"""Parse Terraform / OpenTofu `.tf` files into typed `TerraformResource` objects.

Strategy: run the file through `python-hcl2` to get the parsed body dict, then
regex-scan the original source text for `resource "TYPE" "NAME"` declarations
so we can attach accurate `(line_start, line_end)` source refs to each
resource. python-hcl2 does not expose line info through its public API, so
the regex pass is how we recover it.

v0 scope: `resource` blocks only. `data`, `module`, `locals`, `variable`,
`output`, `provider`, `terraform` blocks are ignored; v1 can add parsers for
whichever detectors need them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import hcl2

from efterlev.errors import DetectorError
from efterlev.models import SourceRef, TerraformResource

_RESOURCE_HEADER_RE = re.compile(r'^\s*resource\s+"([^"]+)"\s+"([^"]+)"')


def parse_terraform_tree(target_dir: Path) -> list[TerraformResource]:
    """Walk `target_dir` recursively and parse every `.tf` file.

    Files that fail to parse raise `DetectorError`; in v0 one bad file fails
    the whole scan so users get a clear signal rather than silent partial
    results. v1 may loosen this to collect-and-continue with warnings.
    """
    if not target_dir.is_dir():
        raise DetectorError(f"target is not a directory: {target_dir}")
    resources: list[TerraformResource] = []
    for tf_file in sorted(target_dir.rglob("*.tf")):
        resources.extend(parse_terraform_file(tf_file))
    return resources


def parse_terraform_file(path: Path) -> list[TerraformResource]:
    """Parse one `.tf` file; return every `resource` block as a typed record."""
    text = path.read_text(encoding="utf-8")
    try:
        with path.open(encoding="utf-8") as f:
            parsed: dict[str, Any] = hcl2.load(f)
    except Exception as e:
        raise DetectorError(f"failed to parse {path}: {e}") from e

    # Build (type, name) -> line_start map by text-scanning the source.
    header_lines: dict[tuple[str, str], int] = {}
    raw_lines = text.splitlines()
    for lineno, raw in enumerate(raw_lines, start=1):
        match = _RESOURCE_HEADER_RE.search(raw)
        if match:
            header_lines.setdefault((match.group(1), match.group(2)), lineno)

    out: list[TerraformResource] = []
    for resource_block in parsed.get("resource", []):
        for rtype, named in resource_block.items():
            for rname, body in named.items():
                actual_body = _unwrap_single_list(body)
                line_start = header_lines.get((rtype, rname))
                line_end = _estimate_block_end(raw_lines, line_start) if line_start else None
                out.append(
                    TerraformResource(
                        type=rtype,
                        name=rname,
                        body=actual_body if isinstance(actual_body, dict) else {},
                        source_ref=SourceRef(
                            file=path,
                            line_start=line_start,
                            line_end=line_end,
                        ),
                    )
                )
    return out


def _unwrap_single_list(value: Any) -> Any:
    """python-hcl2 wraps single attribute values in one-element lists; unwrap them."""
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


def _estimate_block_end(lines: list[str], start: int) -> int:
    """Find the closing `}` for a block that opens on `start` (1-indexed).

    Naive brace-balance — good enough for real-world Terraform because heredoc
    strings are rare and we only need a line range, not an AST. Falls back to
    the last line if no balanced close is found.
    """
    depth = 0
    for offset, line in enumerate(lines[start - 1 :], start=start):
        depth += line.count("{") - line.count("}")
        if depth <= 0 and offset > start:
            return offset
    return len(lines)
