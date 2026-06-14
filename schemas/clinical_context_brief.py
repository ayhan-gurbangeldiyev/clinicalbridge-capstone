from pydantic import BaseModel
from datetime import datetime
from typing import Literal


class RecommendedAction(BaseModel):
    action: str
    rationale: str
    evidence_source: str
    confidence: float


class UncertaintyFlag(BaseModel):
    description: str
    type: Literal["MISSING_DATA", "CONFLICTING_INFO", "LOW_CONFIDENCE"]


class ClinicalContextBrief(BaseModel):
    patient_id: str
    generated_at: datetime
    urgency: Literal["CRITICAL", "URGENT", "ROUTINE", "INFORMATIONAL"]
    alert_summary: dict
    patient_snapshot: dict
    contextual_analysis: str
    risk_assessment: dict
    recommended_actions: list[RecommendedAction]
    uncertainties_and_gaps: list[UncertaintyFlag]
    overall_confidence: float
    immediate_review_required: bool = False
