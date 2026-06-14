from pydantic import BaseModel
from datetime import datetime
from typing import Literal


class RPMAlert(BaseModel):
    patient_id: str
    timestamp: datetime
    device_type: str
    measured_values: dict[str, float]
    alert_category: Literal["CRITICAL", "URGENT", "ROUTINE", "INFORMATIONAL"]
    baseline_thresholds: dict[str, tuple[float, float]]
