"""Per-patient entity memory for the Anamnesis Agent (Module 7: agent memory).

A lightweight, file-backed *entity memory*: it persists a compact set of stable
facts about each patient (last chief complaint, medication-adherence status,
sensitive flags) under ``data/agent_memory/``. On a later interaction with the
same patient the agent can recall these facts and carry context across sessions,
satisfying the brief's requirement to "track patient-reported information over
multiple interactions". Recall returns None on the first-ever interaction, so it
never alters single-pass evaluation runs.
"""

from __future__ import annotations

import json
from pathlib import Path

MEM_DIR = Path("data/agent_memory")


def recall(patient_id: str) -> dict | None:
    """Return remembered facts for a patient, or None if this is the first interaction."""
    f = MEM_DIR / f"{patient_id}.json"
    return json.loads(f.read_text()) if f.exists() else None


def remember(patient_id: str, summary: dict) -> None:
    """Store/refresh the compact entity record for a patient from an AnamnesisSummary."""
    MEM_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "patient_id": patient_id,
        "last_chief_complaint": summary.get("chief_complaint"),
        "last_medication_adherence": summary.get("medication_adherence"),
        "sensitive_flags": summary.get("sensitive_flags", []),
    }
    (MEM_DIR / f"{patient_id}.json").write_text(json.dumps(entry, indent=2))


def clear() -> None:
    """Remove all stored patient memory (used to keep evaluation runs independent)."""
    if MEM_DIR.exists():
        for f in MEM_DIR.glob("*.json"):
            f.unlink()
