"""Generate simulated RPM (Remote Patient Monitoring) time-series data.

Produces a 14-day daily vital-sign stream per patient, ending at the alert
timestamp. For the five scenario patients the series trends from baseline toward
the triggering alert values (so e.g. PT-008's weight gradually climbs and the
final reading is the alert), giving the Triage Agent realistic trend context.
All other patients get stable series around condition-appropriate baselines.

IMPORTANT: every value here is fully synthetic and for educational use only —
no real patient data is involved. Deterministic (seeded) so runs are repeatable.

Run:  PYTHONPATH=. python data/rpm/generate_rpm.py
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

PATIENTS_DIR = Path("data/patients")
SCENARIOS_DIR = Path("data/scenarios")
OUT_DIR = Path("data/rpm")

DAYS = 14
END = datetime(2026, 1, 29, 6, 0, 0)  # series ends at the alert timestamp

# Per-scenario shape of the triggering vital's history:
#   "trend" — a sustained climb from baseline to the alert value (e.g. PT-008 fluid
#             retention: each daily weight is near threshold but steadily rising).
#   "spike" — a stable history with a single isolated exceedance at the latest reading
#             (e.g. PT-005 glucose: one diet-driven blip, not a sustained rise).
# Default is "trend" for scenario patients. Non-triggering vitals stay at baseline.
SCENARIO_PATTERN = {
    "PT-005": "spike",   # false_alarm — isolated, diet-driven glucose blip
}

# Condition-appropriate normal thresholds used when a patient has no scenario alert.
DEFAULT_THRESHOLDS = {
    "systolic_bp": [110.0, 145.0],
    "diastolic_bp": [70.0, 95.0],
    "heart_rate": [50.0, 100.0],
    "spo2": [93.0, 100.0],
    "weight_kg": [60.0, 95.0],
    "glucose_mgdl": [80.0, 180.0],
}


def scenario_alert_for(patient_id: str) -> dict | None:
    """Return the scenario input_alert.json for a patient, if one exists."""
    for scenario in sorted(SCENARIOS_DIR.iterdir()):
        alert_file = scenario / "input_alert.json"
        if alert_file.exists():
            alert = json.loads(alert_file.read_text())
            if alert["patient_id"] == patient_id:
                return alert
    return None


def midpoint(lo: float, hi: float) -> float:
    return (lo + hi) / 2


def generate_series(thresholds: dict, final_values: dict | None, pattern: str) -> list[dict]:
    """14 daily readings. The *triggering* (out-of-range) vitals follow the scenario
    pattern — a sustained climb ("trend") or a stable history with one final spike
    ("spike"); the last reading always equals the alert value. All in-range vitals stay
    near baseline with mild noise."""
    abnormal = {
        v for v, val in (final_values or {}).items()
        if v in thresholds and isinstance(val, (int, float))
        and not (thresholds[v][0] <= val <= thresholds[v][1])
    }
    readings = []
    for day in range(DAYS):
        ts = END - timedelta(days=DAYS - 1 - day)
        is_last = day == DAYS - 1
        values = {}
        for vital, (lo, hi) in thresholds.items():
            base = midpoint(lo, hi)
            if vital in abnormal:
                if is_last:
                    values[vital] = round(final_values[vital], 1)
                    continue
                if pattern == "trend":
                    frac = day / (DAYS - 1)
                    val = base + (final_values[vital] - base) * frac
                else:  # "spike": stable baseline until the final isolated exceedance
                    val = base
            else:
                val = base
            noise = random.uniform(-(hi - lo) * 0.03, (hi - lo) * 0.03)
            values[vital] = round(val + noise, 1)
        readings.append({"timestamp": ts.isoformat(), "values": values})
    return readings


def build_patient_rpm(patient_id: str) -> dict:
    alert = scenario_alert_for(patient_id)
    thresholds = alert["baseline_thresholds"] if alert else DEFAULT_THRESHOLDS
    final_values = alert["measured_values"] if alert else None
    pattern = SCENARIO_PATTERN.get(patient_id, "trend")
    return {
        "patient_id": patient_id,
        "device": {"type": "multiparameter_rpm_hub", "manufacturer": "SimuHealth", "model": "SIM-100"},
        "sampling": "daily",
        "baseline_thresholds": thresholds,
        "readings": generate_series(thresholds, final_values, pattern),
        "note": "Simulated RPM time-series — educational use only, not real patient data.",
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for f in sorted(PATIENTS_DIR.glob("*.json")):
        pid = json.loads(f.read_text())["patient_id"]
        out = OUT_DIR / f"{pid}_rpm.json"
        out.write_text(json.dumps(build_patient_rpm(pid), indent=2))
        print(f"Wrote {out.name} ({DAYS} daily readings)")


if __name__ == "__main__":
    main()
