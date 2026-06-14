import importlib
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from schemas import AnamnesisSummary, TriageDecision
from agents.tools import parse_anamnesis
from agents.memory import recall, remember
from utils.llm_client import get_llm


def _load_prompt(version: str) -> str:
    mod = importlib.import_module(f"prompts.anamnesis.{version}")
    return mod.SYSTEM_PROMPT


class AnamnesisAgent:
    def __init__(self, prompt_version: str = "v1"):
        self.parser = PydanticOutputParser(pydantic_object=AnamnesisSummary)
        self.system_prompt = _load_prompt(prompt_version)

    def run(self, patient_id: str, triage: TriageDecision, config=None) -> AnamnesisSummary:
        # Load the self-reported history via the LangChain data-parsing tool (M7).
        anamnesis_data = parse_anamnesis.invoke({"patient_id": patient_id})
        if not anamnesis_data:
            return AnamnesisSummary(
                patient_id=patient_id,
                chief_complaint="NOT_REPORTED",
                recent_symptoms=[],
                medication_adherence={},
                lifestyle_factors={},
                family_history={},
                patient_concerns="NOT_REPORTED",
                sensitive_flags=[],
                missing_fields=["entire_anamnesis_file_missing"],
            )

        # Recall any prior entity memory for this patient (M7 memory). Empty on the first
        # interaction, so single-pass evaluation runs are unaffected.
        prior = recall(patient_id)
        prior_context = (
            f"Prior recorded context for this patient (from earlier interactions): {json.dumps(prior)}"
            if prior else "No prior recorded context for this patient."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt + "\n\n{format_instructions}"),
            ("human", "Patient ID: {patient_id}\nClinical question: {clinical_question}\nFocus categories: {categories}\n\n{prior_context}\n\nAnamnesis data:\n{anamnesis_json}"),
        ])
        chain = prompt | get_llm(temperature=0) | self.parser
        summary = chain.invoke({
            "format_instructions": self.parser.get_format_instructions(),
            "patient_id": patient_id,
            "clinical_question": triage.clinical_question,
            "categories": ", ".join(triage.anamnesis_categories),
            "prior_context": prior_context,
            "anamnesis_json": json.dumps(anamnesis_data, indent=2),
        }, config=config)

        # Persist a compact entity record so future interactions can recall it (M7 memory).
        remember(patient_id, summary.model_dump())
        return summary
