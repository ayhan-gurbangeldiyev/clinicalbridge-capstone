"""ClinicalBridge — annotated end-to-end demonstration.

Runs the full multi-agent pipeline on two contrasting scenarios and prints a narrated
walkthrough of how a raw RPM alert becomes a Clinical Context Brief. Intended as the
capstone "demonstration" deliverable (record your screen while running it for the video).

Run:  PYTHONPATH=. python demo.py
"""

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from schemas import RPMAlert
from orchestrator.orchestrator import ClinicalBridgeOrchestrator

load_dotenv()

# Two scenarios chosen to show the system's judgement in both directions:
#   silent_deterioration — a mild single reading but a dangerous trend → should ESCALATE
#   false_alarm          — a mild single reading and a benign trend   → should STAY ROUTINE
DEMO_SCENARIOS = [
    ("silent_deterioration",
     "A heart-failure patient. Weight is only 1.7 kg over threshold, but it has climbed "
     "steadily for two weeks. Watch triage use the RPM trend to escalate."),
    ("false_alarm",
     "A diabetic patient. Glucose is 34 mg/dL over threshold, but it is a single diet-driven "
     "spike on an otherwise stable history. Watch the system correctly NOT over-react."),
]

RULE = "=" * 78


def line(label, value):
    print(f"  {label:<22} {value}")


def run_demo(name: str, narration: str):
    print(f"\n{RULE}\nSCENARIO: {name}\n{RULE}")
    print(narration + "\n")

    alert = RPMAlert(**json.loads(Path(f"data/scenarios/{name}/input_alert.json").read_text()))
    print("1) RPM ALERT IN")
    line("patient", alert.patient_id)
    line("measured", json.dumps(alert.measured_values))

    orch = ClinicalBridgeOrchestrator(prompt_version="v4")
    brief = asyncio.run(orch.run(alert, scenario=name))

    # Replay the session log the orchestrator just produced.
    logs = sorted(Path("evaluation/results").glob(f"session_log_{alert.patient_id}_*.json"))
    events = {e["event"]: e["data"] for e in json.loads(logs[-1].read_text())} if logs else {}

    if "triage_complete" in events:
        t = events["triage_complete"]
        print("\n2) TRIAGE AGENT")
        line("urgency", t.get("urgency"))
        line("clinical question", t.get("clinical_question", "")[:90])

    if "ehr_complete" in events:
        e = events["ehr_complete"]
        print("\n3) EHR RETRIEVAL AGENT (RAG)")
        line("active conditions", len(e.get("active_conditions", [])))
        line("retrieval confidence", e.get("retrieval_confidence"))

    if "anamnesis_complete" in events:
        a = events["anamnesis_complete"]
        print("\n4) ANAMNESIS AGENT")
        line("chief complaint", str(a.get("chief_complaint"))[:80])

    print("\n5) SYNTHESIS → CLINICAL CONTEXT BRIEF")
    line("urgency", brief.urgency)
    line("overall confidence", brief.overall_confidence)
    line("immediate review", brief.immediate_review_required)
    print("\n  Contextual analysis:")
    print("    " + brief.contextual_analysis[:400].replace("\n", "\n    "))
    print("\n  Recommended actions:")
    for i, act in enumerate(brief.recommended_actions[:3], 1):
        print(f"    {i}. {act.action[:90]}")
        print(f"       source: {act.evidence_source[:80]}")
    if brief.uncertainties_and_gaps:
        print("\n  Flagged uncertainties:")
        for u in brief.uncertainties_and_gaps[:3]:
            print(f"    - [{u.type}] {u.description[:80]}")


def main():
    print("ClinicalBridge — end-to-end demonstration (prompt version v4, gpt-4o)")
    for name, narration in DEMO_SCENARIOS:
        run_demo(name, narration)
    print(f"\n{RULE}\nDemo complete. Every claim above is cited to a source; no diagnoses are made;\n"
          f"the clinician makes the final decision.\n{RULE}")

    from utils.tracing import flush_langfuse
    flush_langfuse()  # ensure traces reach LangFuse before exit


if __name__ == "__main__":
    main()
