import json
import operator
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional, TypedDict

from langgraph.graph import StateGraph, START, END

from schemas import RPMAlert, TriageDecision, EHRContext, AnamnesisSummary, ClinicalContextBrief, RecommendedAction
from agents.triage_agent import TriageAgent
from agents.ehr_retrieval_agent import EHRRetrievalAgent
from agents.anamnesis_agent import AnamnesisAgent
from agents.synthesis_agent import SynthesisAgent
from utils.tracing import get_langfuse_handler


class ClinicalState(TypedDict):
    """Shared state passed between LangGraph nodes.

    ``session_log`` uses ``operator.add`` as its reducer so the parallel EHR and
    Anamnesis nodes can each append events without overwriting one another.
    """
    alert: RPMAlert
    triage: Optional[TriageDecision]
    ehr_context: Optional[EHRContext]
    anamnesis_summary: Optional[AnamnesisSummary]
    brief: Optional[ClinicalContextBrief]
    session_log: Annotated[list[dict], operator.add]


def _event(event: str, data: dict) -> dict:
    return {
        "event": event,
        "timestamp": datetime.now().isoformat(),
        "data": data,
    }


class ClinicalBridgeOrchestrator:
    """Coordinates the four agents as a LangGraph state machine.

    Flow: triage -> (CRITICAL? escalate : EHR ∥ Anamnesis) -> synthesis.
    EHR and Anamnesis run in parallel within a single LangGraph super-step
    (fan-out from triage, fan-in at synthesis), replacing the previous manual
    ``asyncio.gather`` orchestration.
    """

    def __init__(self, prompt_version: str = "v1"):
        self.prompt_version = prompt_version
        self.triage = TriageAgent(prompt_version)
        self.ehr = EHRRetrievalAgent(prompt_version)
        self.anamnesis = AnamnesisAgent(prompt_version)
        self.synthesis = SynthesisAgent(prompt_version)
        self.graph = self._build_graph()

    # ------------------------------------------------------------------ nodes
    # Each node receives the RunnableConfig from LangGraph and forwards it to the
    # agent's chain.invoke so the LangFuse callback propagates down to the LLM call
    # (otherwise the inner generations — and their token usage/cost — aren't traced).
    def _triage_node(self, state: ClinicalState, config) -> dict:
        alert = state["alert"]
        triage = self.triage.run(alert, config=config)
        return {
            "triage": triage,
            "session_log": [
                _event("alert_received", alert.model_dump()),
                _event("triage_complete", triage.model_dump()),
            ],
        }

    def _ehr_node(self, state: ClinicalState, config) -> dict:
        ehr_context = self.ehr.run(state["alert"].patient_id, state["triage"], config=config)
        return {
            "ehr_context": ehr_context,
            "session_log": [_event("ehr_complete", ehr_context.model_dump())],
        }

    def _anamnesis_node(self, state: ClinicalState, config) -> dict:
        anamnesis_summary = self.anamnesis.run(state["alert"].patient_id, state["triage"], config=config)
        return {
            "anamnesis_summary": anamnesis_summary,
            "session_log": [_event("anamnesis_complete", anamnesis_summary.model_dump())],
        }

    def _synthesis_node(self, state: ClinicalState, config) -> dict:
        brief = self.synthesis.run(
            state["alert"],
            state["triage"],
            state["ehr_context"],
            state["anamnesis_summary"],
            config=config,
        )
        return {
            "brief": brief,
            "session_log": [_event("brief_generated", brief.model_dump())],
        }

    def _escalate_node(self, state: ClinicalState) -> dict:
        brief = self._escalate(state["alert"], state["triage"])
        return {
            "brief": brief,
            "session_log": [_event("brief_generated", brief.model_dump())],
        }

    @staticmethod
    def _route_after_triage(state: ClinicalState) -> list[str]:
        """CRITICAL alerts bypass retrieval/synthesis and escalate immediately;
        all others fan out to EHR and Anamnesis in parallel."""
        if state["triage"].urgency == "CRITICAL":
            return ["escalate"]
        return ["ehr", "anamnesis"]

    def _build_graph(self):
        builder = StateGraph(ClinicalState)
        builder.add_node("triage", self._triage_node)
        builder.add_node("ehr", self._ehr_node)
        builder.add_node("anamnesis", self._anamnesis_node)
        builder.add_node("synthesis", self._synthesis_node)
        builder.add_node("escalate", self._escalate_node)

        builder.add_edge(START, "triage")
        builder.add_conditional_edges(
            "triage",
            self._route_after_triage,
            ["ehr", "anamnesis", "escalate"],
        )
        builder.add_edge("ehr", "synthesis")
        builder.add_edge("anamnesis", "synthesis")
        builder.add_edge("synthesis", END)
        builder.add_edge("escalate", END)
        return builder.compile()

    # ------------------------------------------------------------------- run
    async def run(self, alert: RPMAlert, scenario: Optional[str] = None) -> ClinicalContextBrief:
        config = {
            "metadata": {
                "patient_id": alert.patient_id,
                "prompt_version": self.prompt_version,
                "scenario": scenario,
            }
        }
        handler = get_langfuse_handler()
        if handler is not None:
            config["callbacks"] = [handler]

        final_state = await self.graph.ainvoke(
            {"alert": alert, "session_log": []},
            config=config,
        )
        self._save_log(alert.patient_id, final_state["session_log"])
        return final_state["brief"]

    def _escalate(self, alert: RPMAlert, triage) -> ClinicalContextBrief:
        return ClinicalContextBrief(
            patient_id=alert.patient_id,
            generated_at=datetime.now(),
            urgency="CRITICAL",
            alert_summary={
                "triggered_by": str(alert.measured_values),
                "urgency": "CRITICAL",
                "timestamp": str(alert.timestamp),
            },
            patient_snapshot={},
            contextual_analysis="CRITICAL alert — immediate escalation. Synthesis bypassed.",
            risk_assessment={"confidence": 1.0, "notes": "CRITICAL urgency — no further analysis needed before escalation"},
            recommended_actions=[
                RecommendedAction(
                    action="Immediate clinical escalation",
                    rationale="CRITICAL alert threshold exceeded",
                    evidence_source=f"RPM: {alert.measured_values}",
                    confidence=1.0,
                )
            ],
            uncertainties_and_gaps=[],
            overall_confidence=1.0,
            immediate_review_required=True,
        )

    def _save_log(self, patient_id: str, session_log: list[dict]):
        Path("evaluation/results").mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = Path(f"evaluation/results/session_log_{patient_id}_{ts}.json")
        with open(out, "w") as f:
            json.dump(session_log, f, indent=2, default=str)
