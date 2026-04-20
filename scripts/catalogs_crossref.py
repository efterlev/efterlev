"""Cross-reference every 800-53 control ID cited by a KSI in the vendored FRMR against
the vendored NIST SP 800-53 Rev 5 catalog.

A KSI whose `controls` list cites an ID that does not resolve in the 800-53 catalog is a
data-integrity bug the FRMR and 800-53 loaders will hit on Day 1. Running this pre-hackathon
catches those bugs against the pinned versions so the hackathon doesn't have to debug them.

Run: `uv run python scripts/catalogs_crossref.py`
Exit code 0 = clean; 1 = at least one KSI cites a non-existent control.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from trestle.oscal.catalog import Catalog, Control

FRMR_PATH = Path(__file__).resolve().parents[1] / "catalogs" / "frmr" / "FRMR.documentation.json"
NIST_PATH = (
    Path(__file__).resolve().parents[1] / "catalogs" / "nist" / "NIST_SP-800-53_rev5_catalog.json"
)


def collect_800_53_ids(catalog: Catalog) -> set[str]:
    """Walk the catalog and return every control + enhancement id as a set."""
    ids: set[str] = set()

    def walk(controls: list[Control] | None) -> None:
        if not controls:
            return
        for c in controls:
            ids.add(c.id)
            walk(c.controls)

    for group in catalog.groups or []:
        walk(group.controls)
    return ids


def main() -> int:
    if not FRMR_PATH.exists() or not NIST_PATH.exists():
        raise SystemExit("catalogs not found; expected at catalogs/frmr/ and catalogs/nist/")

    frmr = json.loads(FRMR_PATH.read_text())
    catalog = Catalog.oscal_read(NIST_PATH)
    nist_ids = collect_800_53_ids(catalog)

    cited_by_ksi: dict[str, list[str]] = defaultdict(list)
    missing_by_ksi: dict[str, list[str]] = defaultdict(list)
    all_cited: set[str] = set()

    for theme in frmr.get("KSI", {}).values():
        for ksi_id, ksi in theme.get("indicators", {}).items():
            for ctrl in ksi.get("controls", []):
                cited_by_ksi[ksi_id].append(ctrl)
                all_cited.add(ctrl)
                if ctrl not in nist_ids:
                    missing_by_ksi[ksi_id].append(ctrl)

    total_ksis = sum(len(t.get("indicators", {})) for t in frmr.get("KSI", {}).values())

    print(f"FRMR version:      {frmr.get('info', {}).get('version')}")
    print(f"FRMR last_updated: {frmr.get('info', {}).get('last_updated')}")
    print(f"KSI indicators:    {total_ksis}")
    print(f"Unique 800-53 IDs cited by any KSI: {len(all_cited)}")
    print(f"800-53 catalog IDs (incl. enhancements): {len(nist_ids)}")
    print()

    if missing_by_ksi:
        total_missing = sum(len(v) for v in missing_by_ksi.values())
        print(f"MISMATCHES — {total_missing} cited IDs do NOT resolve in 800-53:")
        for ksi_id, missing in sorted(missing_by_ksi.items()):
            for m in missing:
                print(f"  {ksi_id}  ->  {m}  (not in catalog)")
        return 1

    print("OK — every control ID cited by any KSI resolves in the 800-53 catalog.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
