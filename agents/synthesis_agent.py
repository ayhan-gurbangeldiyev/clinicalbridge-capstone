import importlib

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from schemas import RPMAlert, TriageDecision, EHRContext, AnamnesisSummary, ClinicalContextBrief
from utils.llm_client import get_llm


def _load_prompt(version: str) -> str:
    mod = importlib.import_module(f"prompts.synthesis.{version}")
    return mod.SYSTEM_PROMPT


class SynthesisAgent:
    def __init__(self, prompt_version: str = "v1"):
        self.parser = PydanticOutputParser(pydantic_object=ClinicalContextBrief)
        self.system_prompt = _load_prompt(prompt_version)

    def run(
        self,
        alert: RPMAlert,
        triage: TriageDecision,
        ehr: EHRContext,
        anamnesis: AnamnesisSummary,
        config=None,
    ) -> ClinicalContextBrief:
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt + "\n\n{format_instructions}"),
            ("human", (
                "RPM Alert:\n{alert_json}\n\n"
                "Triage Decision:\n{triage_json}\n\n"
                "EHR Context:\n{ehr_json}\n\n"
                "Anamnesis Summary:\n{anamnesis_json}"
            )),
        ])
        chain = prompt | get_llm(temperature=0.1) | self.parser
        return chain.invoke({
            "format_instructions": self.parser.get_format_instructions(),
            "alert_json": alert.model_dump_json(),
            "triage_json": triage.model_dump_json(),
            "ehr_json": ehr.model_dump_json(),
            "anamnesis_json": anamnesis.model_dump_json(),
        }, config=config)
