from __future__ import annotations
from typing import Union
from pydantic import BaseModel


class AnamnesisSummary(BaseModel):
    patient_id: str
    chief_complaint: str
    recent_symptoms: list[dict]
    medication_adherence: Union[dict, str]
    lifestyle_factors: Union[dict, str]
    family_history: Union[dict, str]
    patient_concerns: str
    sensitive_flags: list[str]
    missing_fields: list[str]
