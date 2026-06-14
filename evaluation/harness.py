import asyncio
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from schemas import RPMAlert
from orchestrator.orchestrator import ClinicalBridgeOrchestrator
from rag.retriever import retrieve
from evaluation.metrics import (
    triage_accuracy,
    hallucination_rate,
    anamnesis_completeness,
    retrieval_precision,
    retrieval_recall,
)

SCENARIOS = [
    "missed_medication",
    "false_alarm",
    "silent_deterioration",
    "incomplete_record",
    "conflicting_data",
]

GOLD_URGENCY = {
    "missed_medication": "URGENT",
    "false_alarm": "ROUTINE",
    "silent_deterioration": "URGENT",
    "incomplete_record": "URGENT",
    "conflicting_data": "URGENT",
}

# Gold-standard relevant *facts* per scenario — the key pieces of EHR content the retriever
# must surface for the clinical question. Defined as case-insensitive substrings so the
# metric is robust to chunking changes (Brief Ch. 9.1 defines recall over "relevant EHR
# facts", precision over "retrieved chunks relevant to the question").
GOLD_FACTS = {
    "missed_medication": ["lisinopril", "cough"],          # PT-001: ACE inhibitor + its cough side effect
    "false_alarm": ["vacation", "hba1c"],                  # PT-005: diet/vacation context + recent lab
    "silent_deterioration": ["furosemide", "weight"],      # PT-008: diuretic + weight/fluid status
    "incomplete_record": ["transfer", "overseas"],         # PT-012: sparse transfer-of-care record
    "conflicting_data": ["sub-therapeutic", "adherence"],  # PT-011: drug-level lab + adherence discrepancy
}


def run_scenario(name: str, version: str = "v1") -> dict:
    alert_path = Path(f"data/scenarios/{name}/input_alert.json")
    alert = RPMAlert(**json.loads(alert_path.read_text()))
    orchestrator = ClinicalBridgeOrchestrator(version)

    t0 = time.time()
    brief = asyncio.run(orchestrator.run(alert, scenario=name))
    elapsed = round(time.time() - t0, 2)

    actions = [a.model_dump() for a in brief.recommended_actions]
    h_rate = hallucination_rate(actions)

    # Source traceability: proportion of actions with a non-empty evidence_source
    traceable = sum(1 for a in actions if a.get("evidence_source", "").strip())
    traceability = traceable / len(actions) if actions else 1.0

    # Load the most recent session log for this patient (written during the run above).
    session_logs = sorted(
        Path("evaluation/results").glob(f"session_log_{alert.patient_id}_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    log = json.loads(session_logs[0].read_text()) if session_logs else []

    # Anamnesis completeness measured against the ACTUAL AnamnesisSummary produced by the
    # agent (from the session log), not a proxy derived from the final brief.
    anam_event = next((e for e in log if e["event"] == "anamnesis_complete"), None)
    a_completeness = anamnesis_completeness(anam_event["data"]) if anam_event else 0.0

    # Retrieval precision/recall measured on the REAL RAG output (deterministic), content-based
    # per the brief's definitions: recall = fraction of gold facts present in any retrieved
    # chunk; precision = fraction of retrieved chunks that contain at least one gold fact.
    r_precision, r_recall = None, None
    triage_event = next((e for e in log if e["event"] == "triage_complete"), None)
    facts = [f.lower() for f in GOLD_FACTS.get(name, [])]
    if triage_event and facts:
        try:
            q = triage_event["data"]["clinical_question"]
            texts = [c["content"].lower() for c in retrieve(alert.patient_id, q)]
            if texts:
                found = sum(1 for f in facts if any(f in t for t in texts))
                rel_chunks = sum(1 for t in texts if any(f in t for f in facts))
                r_recall = round(found / len(facts), 2)
                r_precision = round(rel_chunks / len(texts), 2)
        except Exception:
            pass

    passed = brief.overall_confidence >= 0.6 and h_rate <= 0.1

    return {
        "scenario": name,
        "urgency": brief.urgency,
        "gold_urgency": GOLD_URGENCY.get(name, "UNKNOWN"),
        "overall_confidence": brief.overall_confidence,
        "hallucination_rate": h_rate,
        "source_traceability": round(traceability, 2),
        "anamnesis_completeness": round(a_completeness, 2),
        "retrieval_precision": round(r_precision, 2) if r_precision is not None else "N/A",
        "retrieval_recall": round(r_recall, 2) if r_recall is not None else "N/A",
        "time_to_brief_s": elapsed,
        "immediate_review_required": brief.immediate_review_required,
        "passed": passed,
        "brief": brief.model_dump(),
    }


def run_all(version: str = "v1"):
    load_dotenv()
    # Start each evaluation run from a clean memory so runs are independent.
    from agents import memory
    memory.clear()
    results = []
    for name in SCENARIOS:
        print(f"Running scenario: {name} ...", end=" ", flush=True)
        try:
            r = run_scenario(name, version)
            results.append(r)
            status = "PASS" if r["passed"] else "FAIL"
            print(f"{status} | conf={r['overall_confidence']:.2f} | hall={r['hallucination_rate']:.2f} | {r['time_to_brief_s']}s")
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({"scenario": name, "passed": False, "error": str(e)})

    valid = [r for r in results if "urgency" in r]
    passed_count = sum(r.get("passed", False) for r in results)

    preds = [r["urgency"] for r in valid]
    golds = [r["gold_urgency"] for r in valid]
    t_acc = triage_accuracy(preds, golds) if preds else 0.0

    avg_hall = sum(r.get("hallucination_rate", 0) for r in valid) / len(valid) if valid else 0.0
    avg_trace = sum(r.get("source_traceability", 0) for r in valid) / len(valid) if valid else 0.0
    avg_comp = sum(r.get("anamnesis_completeness", 0) for r in valid) / len(valid) if valid else 0.0
    avg_time = sum(r.get("time_to_brief_s", 0) for r in valid) / len(valid) if valid else 0.0

    prec_vals = [r["retrieval_precision"] for r in valid if isinstance(r.get("retrieval_precision"), float)]
    rec_vals = [r["retrieval_recall"] for r in valid if isinstance(r.get("retrieval_recall"), float)]
    avg_prec = sum(prec_vals) / len(prec_vals) if prec_vals else None
    avg_rec = sum(rec_vals) / len(rec_vals) if rec_vals else None

    print(f"\n{'='*55}")
    print(f"  EVALUATION SUMMARY — prompt version: {version}")
    print(f"{'='*55}")
    print(f"  Scenario pass rate     : {passed_count}/{len(results)}  (target ≥4/5)")
    print(f"  Triage accuracy        : {t_acc:.0%}  (target ≥90%)")
    print(f"  Hallucination rate     : {avg_hall:.1%}  (target ≤5%)")
    print(f"  Source traceability    : {avg_trace:.0%}  (target ≥90%)")
    print(f"  Anamnesis completeness : {avg_comp:.0%}  (target ≥85%)")
    print(f"  Avg time-to-brief      : {avg_time:.1f}s  (target <30s)")
    if avg_prec is not None:
        print(f"  Retrieval precision    : {avg_prec:.0%}  (target ≥80%)")
        print(f"  Retrieval recall       : {avg_rec:.0%}  (target ≥75%)")
    else:
        print(f"  Retrieval precision    : N/A (run ingest first)")
        print(f"  Retrieval recall       : N/A (run ingest first)")
    print(f"{'='*55}")

    Path("evaluation/results").mkdir(exist_ok=True)
    out = Path(f"evaluation/results/run_{version}.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {out}")

    from utils.tracing import flush_langfuse
    flush_langfuse()  # ensure all traces reach LangFuse before exit
    return results


if __name__ == "__main__":
    v = sys.argv[1] if len(sys.argv) > 1 else "v4"
    run_all(v)
