import importlib
import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from schemas import EHRContext, TriageDecision
from agents.tools import vector_store_search
from utils.llm_client import get_llm


def _load_prompt(version: str) -> str:
    mod = importlib.import_module(f"prompts.ehr.{version}")
    return mod.SYSTEM_PROMPT


class EHRRetrievalAgent:
    def __init__(self, prompt_version: str = "v1"):
        self.parser = PydanticOutputParser(pydantic_object=EHRContext)
        self.system_prompt = _load_prompt(prompt_version)
        self.persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./vectorstore")

    def run(self, patient_id: str, triage: TriageDecision, config=None) -> EHRContext:
        # Retrieve EHR context via the LangChain vector-store-search tool (M7).
        chunks_text = vector_store_search.invoke({
            "patient_id": patient_id,
            "query": triage.clinical_question,
        })
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt + "\n\n{format_instructions}"),
            ("human", "Patient ID: {patient_id}\nClinical question: {clinical_question}\n\nRetrieved EHR chunks:\n{chunks}"),
        ])
        chain = prompt | get_llm(temperature=0) | self.parser
        return chain.invoke({
            "format_instructions": self.parser.get_format_instructions(),
            "patient_id": patient_id,
            "clinical_question": triage.clinical_question,
            "chunks": chunks_text,
        }, config=config)
