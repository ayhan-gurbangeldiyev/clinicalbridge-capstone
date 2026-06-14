from pydantic import BaseModel
from typing import Literal


class TriageDecision(BaseModel):
    patient_id: str
    urgency: Literal["CRITICAL", "URGENT", "ROUTINE", "INFORMATIONAL"]
    reasoning: str
    clinical_question: str
    ehr_query_params: dict[str, str]
    anamnesis_categories: list[str]
