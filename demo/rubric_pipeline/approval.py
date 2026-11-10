"""Teacher approval gate: grading may only use a rubric a teacher has approved, unchanged.

Approval stores a SHA-256 fingerprint of the exact structured rubric. If the rubric file is
edited afterwards, the fingerprint no longer matches and grading is refused until a teacher
approves the new version. (In this demo the teacher's name is typed on the command line; in
localEd the approving teacher would be the signed-in Google Chat user.)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


class NotApproved(PermissionError):
    pass


def fingerprint(rubric_json: Path) -> str:
    return hashlib.sha256(rubric_json.read_bytes()).hexdigest()


def approval_path(rubric_json: Path) -> Path:
    return rubric_json.with_name(rubric_json.stem + ".approval.json")


def approve(rubric_json: Path, teacher: str, has_errors: bool) -> Path:
    if has_errors:
        raise NotApproved("This rubric has validation errors; fix the source document first.")
    if not teacher.strip():
        raise NotApproved("Approval needs the teacher's name.")
    record = {"rubric": rubric_json.name, "sha256": fingerprint(rubric_json),
              "approved_by": teacher.strip(),
              "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    path = approval_path(rubric_json)
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return path


def require_approval(rubric_json: Path) -> dict:
    """Return the approval record, or raise NotApproved with a teacher-friendly reason."""
    path = approval_path(rubric_json)
    if not path.exists():
        raise NotApproved("Not approved yet: a teacher must review and approve this rubric first.")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("sha256") != fingerprint(rubric_json):
        raise NotApproved("The rubric changed after it was approved; it must be approved again.")
    return record
