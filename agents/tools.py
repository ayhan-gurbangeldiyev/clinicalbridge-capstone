"""LangChain tools used by the agents (Module 7: tool integration).

These wrap the three capabilities the capstone brief lists as agent tools —
vector-store search, alert classification, and data parsing — as proper
LangChain ``StructuredTool`` objects (via the ``@tool`` decorator). Agents invoke
them deterministically (``tool.invoke({...})``) so behaviour stays testable and
reproducible while still exercising the LangChain tool interface.
"""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import tool

from rag.retriever import retrieve as _retrieve


@tool
def vector_store_search(patient_id: str, query: str) -> str:
    """Search the patient's EHR vector store (ChromaDB RAG) for chunks relevant to a
    clinical question. Returns the top chunk excerpts with similarity scores."""
    chunks = _retrieve(patient_id, query)
    return "\n\n".join(
        f"[chunk_{c['chunk_id']} score={c['score']:.2f}]\n{c['content']}" for c in chunks
    )


@tool
def alert_classification(measured_values: dict, baseline_thresholds: dict) -> str:
    """Compute, per vital, how far a measured value deviates from its baseline range
    (direction + absolute amount). A deterministic helper that grounds the Triage Agent's
    urgency reasoning so it does not have to do the arithmetic itself."""
    lines = []
    for vital, value in measured_values.items():
        rng = baseline_thresholds.get(vital)
        if not rng or not isinstance(value, (int, float)):
            lines.append(f"{vital}: {value} (no threshold)")
            continue
        lo, hi = rng
        if value < lo:
            lines.append(f"{vital}: {value} BELOW range [{lo}, {hi}] by {round(lo - value, 1)}")
        elif value > hi:
            lines.append(f"{vital}: {value} ABOVE range [{lo}, {hi}] by {round(value - hi, 1)}")
        else:
            lines.append(f"{vital}: {value} within range [{lo}, {hi}]")
    return "\n".join(lines)


@tool
def rpm_trend(patient_id: str, measured_values: dict, baseline_thresholds: dict) -> str:
    """Summarize the recent RPM history for each out-of-range vital: whether it is a
    sustained upward trend or a single isolated spike. Lets the Triage Agent reason about
    trajectories (e.g. gradual weight gain in heart failure) rather than one reading alone."""
    path = Path(f"data/rpm/{patient_id}_rpm.json")
    if not path.exists():
        return "No RPM history available."
    readings = json.loads(path.read_text()).get("readings", [])
    lines = []
    for vital, value in measured_values.items():
        rng = baseline_thresholds.get(vital)
        if not rng or not isinstance(value, (int, float)) or rng[0] <= value <= rng[1]:
            continue  # only summarize abnormal (triggering) vitals
        lo, hi = rng
        series = [r["values"][vital] for r in readings if vital in r.get("values", {})]
        if len(series) < 3:
            continue
        first, last = series[0], series[-1]
        delta = round(last - first, 1)
        above = sum(1 for x in series if x > hi or x < lo)
        if above <= 1:
            shape = f"STABLE history with a single isolated reading out of range now (latest {last})"
        elif delta > 0 and above >= 3:
            shape = f"SUSTAINED UPWARD TREND over {len(series)} readings (+{delta}, from {first} to {last})"
        elif delta < 0 and above >= 3:
            shape = f"sustained downward trend over {len(series)} readings ({delta}, from {first} to {last})"
        else:
            shape = f"fluctuating over {len(series)} readings (from {first} to {last})"
        lines.append(f"{vital}: {shape}")
    return "\n".join(lines) if lines else "No sustained out-of-range trend in recent RPM history."


@tool
def parse_anamnesis(patient_id: str) -> dict:
    """Load and parse the patient's structured anamnesis (self-reported history) record.
    Returns an empty dict if no record exists for the patient."""
    path = Path(f"data/anamnesis/{patient_id}_anamnesis.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text())
