from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class LabResult(BaseModel):
    test: str
    value: str
    date: str
    trend: Optional[str] = None
    chunk_id: str = ""


class EHRContext(BaseModel):
    patient_id: str
    active_conditions: list[dict]
    current_medications: list[dict]
    recent_labs: list[LabResult]
    relevant_notes: list[dict]
    retrieval_confidence: float
    missing_data_flags: list[str]
