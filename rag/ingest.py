import json
import os
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from rag.config import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL, CHROMA_COLLECTION_PREFIX
from utils.llm_client import get_embeddings


def ehr_to_text(p: dict) -> str:
    parts = []
    d = p.get("demographics", {})
    parts.append(f"Patient: {d.get('name','unknown')}, age {d.get('age','?')}, sex {d.get('sex','?')}")

    problems = p.get("problem_list", [])
    if problems:
        parts.append("Problem list: " + "; ".join(f"{x['label']} ({x['icd10']})" for x in problems))

    meds = p.get("medications", [])
    if meds:
        parts.append("Medications: " + "; ".join(f"{x['name']} {x['dose']} {x['frequency']}" for x in meds))

    allergies = p.get("allergies", [])
    if allergies:
        parts.append("Allergies: " + "; ".join(f"{x['allergen']} - {x['reaction']}" for x in allergies))

    for lab in p.get("labs", []):
        results_str = ", ".join(f"{k}={v}" for k, v in lab.get("results", {}).items())
        parts.append(f"Lab {lab['test']} on {lab['date']}: {results_str}")

    for note in p.get("visit_notes", []):
        parts.append(f"Visit note {note['date']}: {note['note']}")

    return "\n".join(parts)


def ingest_patient(patient_id: str, patient_data: dict, persist_dir: str):
    text = ehr_to_text(patient_data)
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.create_documents(
        [text],
        metadatas=[{"patient_id": patient_id, "chunk_index": i} for i in range(1)]
    )
    # re-split to get correct chunk count with metadata
    raw_chunks = splitter.split_text(text)
    from langchain_core.documents import Document
    docs = [
        Document(page_content=chunk, metadata={"patient_id": patient_id, "chunk_index": i})
        for i, chunk in enumerate(raw_chunks)
    ]

    embeddings = get_embeddings()
    collection = f"{CHROMA_COLLECTION_PREFIX}{patient_id}"
    # Idempotent: clear any existing collection so re-ingesting does not append duplicate
    # chunks (Chroma.from_documents adds to an existing collection rather than replacing it).
    try:
        Chroma(collection_name=collection, embedding_function=embeddings,
               persist_directory=persist_dir).delete_collection()
    except Exception:
        pass
    Chroma.from_documents(
        docs,
        embeddings,
        collection_name=collection,
        persist_directory=persist_dir
    )


def ingest_all(data_dir: str = "data/patients", persist_dir: str = "./vectorstore"):
    for f in sorted(Path(data_dir).glob("*.json")):
        patient = json.loads(f.read_text())
        pid = patient["patient_id"]
        ingest_patient(pid, patient, persist_dir)
        print(f"Ingested {pid}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    ingest_all()
