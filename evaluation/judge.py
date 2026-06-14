"""LLM-as-judge evaluation for the agent-level metrics that need qualitative review
(Brief Ch. 9.1): Triage *query relevance*, Anamnesis *interpretation accuracy*, and
Synthesis *clinical accuracy*. These cannot be checked with simple string comparisons, so a
gpt-4o judge scores each agent's output for the latest run of every scenario against the
source data and the gold-standard brief.

Run:  PYTHONPATH=. python evaluation/judge.py
Reads the most recent session log per scenario patient (produce them with
`python evaluation/harness.py v4` first) and the gold CCBs.
"""

import json
import re
from pathlib import Path

from dotenv import load_dotenv

from utils.llm_client import get_llm

SCENARIOS = {
    "missed_medication": "PT-001",
    "false_alarm": "PT-005",
    "silent_deterioration": "PT-008",
    "incomplete_record": "PT-012",
    "conflicting_data": "PT-011",
}

JUDGE_PROMPT = """You are a clinical evaluation judge. Score the outputs of an LLM clinical
assistant against the source data and the gold-standard brief. Be strict and objective.

Return ONLY valid JSON with this exact shape:
{{
  "triage_query_relevance": <integer 1-5>,        // is the triage clinical question clinically appropriate and useful for guiding retrieval for this alert?
  "anamnesis_interpretation_accuracy": <float 0-1>, // did the anamnesis summary correctly map the patient's reported language into clinical concepts, without distortion?
  "synthesis_clinical_accuracy": <float 0-1>,       // FACTUAL CORRECTNESS of the claims the brief makes, against the source data (this is the brief's per-Ch.9.1 definition). Score by accuracy ONLY: 1.0 = every stated claim is factually correct and supported by the source; deduct ONLY for claims that are wrong, unsupported, or contradicted by the source. Do NOT deduct for brevity, omitted nuances, or missing details — completeness is a SEPARATE metric, not part of accuracy.
  "notes": "<one sentence justification focused on factual correctness of stated claims>"
}}

RPM ALERT:
{alert}

TRIAGE clinical question:
{triage_q}

ANAMNESIS summary produced:
{anamnesis}

CLINICAL CONTEXT BRIEF produced (contextual analysis + actions):
{brief}

GOLD-STANDARD BRIEF (reference):
{gold}
"""


def _latest_log(pid: str):
    logs = sorted(Path("evaluation/results").glob(f"session_log_{pid}_*.json"),
                  key=lambda p: p.stat().st_mtime)
    return json.loads(logs[-1].read_text()) if logs else None


def _event(log, name):
    return next((e["data"] for e in log if e["event"] == name), {})


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(m.group(0)) if m else {}


def judge_scenario(name: str, pid: str) -> dict:
    log = _latest_log(pid)
    if not log:
        return {"scenario": name, "error": "no session log"}
    alert = _event(log, "alert_received")
    triage = _event(log, "triage_complete")
    anamnesis = _event(log, "anamnesis_complete")
    brief = _event(log, "brief_generated")
    gold_path = Path(f"data/scenarios/{name}/gold_standard_ccb.md")
    gold = gold_path.read_text()[:4000] if gold_path.exists() else "(no gold brief)"

    prompt = JUDGE_PROMPT.format(
        alert=json.dumps(alert.get("measured_values", alert))[:600],
        triage_q=triage.get("clinical_question", ""),
        anamnesis=json.dumps(anamnesis)[:2000],
        brief=json.dumps({
            "contextual_analysis": brief.get("contextual_analysis", ""),
            "recommended_actions": brief.get("recommended_actions", []),
        })[:2500],
        gold=gold,
    )
    # Sample the judge 3x (with mild temperature) and average to reduce single-shot noise.
    samples = []
    for _ in range(3):
        s = _parse_json(get_llm(temperature=0.4).invoke(prompt).content)
        if s:
            samples.append(s)

    def avg(k):
        vals = [s[k] for s in samples if isinstance(s.get(k), (int, float))]
        return round(sum(vals) / len(vals), 2) if vals else None

    return {
        "scenario": name,
        "triage_query_relevance": avg("triage_query_relevance"),
        "anamnesis_interpretation_accuracy": avg("anamnesis_interpretation_accuracy"),
        "synthesis_clinical_accuracy": avg("synthesis_clinical_accuracy"),
        "n_samples": len(samples),
        "notes": samples[-1].get("notes", "") if samples else "no valid judge output",
    }


def main():
    load_dotenv()
    results = [judge_scenario(n, p) for n, p in SCENARIOS.items()]
    valid = [r for r in results if "error" not in r]

    def avg(k):
        vals = [r[k] for r in valid if isinstance(r.get(k), (int, float))]
        return sum(vals) / len(vals) if vals else 0.0

    print("\n" + "=" * 60)
    print("  AGENT-LEVEL LLM-AS-JUDGE EVALUATION (gpt-4o judge)")
    print("=" * 60)
    for r in results:
        if "error" in r:
            print(f"  {r['scenario']:22} ERROR: {r['error']}")
        else:
            print(f"  {r['scenario']:22} query_rel={r.get('triage_query_relevance')}/5 "
                  f"interp={r.get('anamnesis_interpretation_accuracy')} "
                  f"clinical_acc={r.get('synthesis_clinical_accuracy')}")
    print("-" * 60)
    print(f"  Triage query relevance     : {avg('triage_query_relevance'):.1f}/5   (target ≥4/5)")
    print(f"  Anamnesis interpretation   : {avg('anamnesis_interpretation_accuracy'):.0%}   (target ≥80%)")
    print(f"  Synthesis clinical accuracy: {avg('synthesis_clinical_accuracy'):.0%}   (target ≥90%)")
    print("=" * 60)

    out = Path("evaluation/results/judge_v4.json")
    out.write_text(json.dumps(results, indent=2))
    print(f"Saved to {out}")

    from utils.tracing import flush_langfuse
    flush_langfuse()


if __name__ == "__main__":
    main()
