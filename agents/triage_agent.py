import importlib

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from schemas import RPMAlert, TriageDecision
from agents.tools import alert_classification, rpm_trend
from utils.llm_client import get_llm


def _load_prompt(version: str) -> str:
    mod = importlib.import_module(f"prompts.triage.{version}")
    return mod.SYSTEM_PROMPT


class TriageAgent:
    def __init__(self, prompt_version: str = "v1"):
        self.parser = PydanticOutputParser(pydantic_object=TriageDecision)
        self.prompt_version = prompt_version
        self.system_prompt = _load_prompt(prompt_version)

    def run(self, alert: RPMAlert, config=None) -> TriageDecision:
        # Pre-compute per-vital deviations with the alert-classification tool (M7) so the
        # LLM reasons over explicit numbers rather than doing the arithmetic itself.
        deviations = alert_classification.invoke({
            "measured_values": alert.measured_values,
            "baseline_thresholds": alert.baseline_thresholds,
        })
        # v4 is trend-aware: summarize the recent RPM history so triage can escalate on a
        # sustained trend (not just the single reading). Earlier versions are unchanged.
        human = "{alert_json}\n\nComputed deviations from baseline:\n{deviations}"
        payload = {
            "format_instructions": self.parser.get_format_instructions(),
            "alert_json": alert.model_dump_json(),
            "deviations": deviations,
        }
        # v4 is trend-aware: summarize the recent RPM history so triage can escalate on a
        # sustained trend (not just the single reading). Earlier versions are unchanged.
        if self.prompt_version == "v4":
            payload["trend"] = rpm_trend.invoke({
                "patient_id": alert.patient_id,
                "measured_values": alert.measured_values,
                "baseline_thresholds": alert.baseline_thresholds,
            })
            human += "\n\nRecent RPM trend:\n{trend}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt + "\n\n{format_instructions}"),
            ("human", human),
        ])
        chain = prompt | get_llm(temperature=0) | self.parser
        try:
            return chain.invoke(payload, config=config)
        except Exception:
            return chain.invoke(payload, config=config)
