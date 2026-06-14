<p align="center">
  <img src="assets/langchain-logo.png" width="120" height="120" alt="LangChain" />
</p>

# ClinicalBridge

**An LLM-Powered Multi-Agent System for Synthesizing Electronic Health Records, Remote Patient Monitoring, and Anamnesis Data**

> COP-3442 Prompt Engineering — Capstone Project  
> Bahçeşehir University, Artificial Intelligence Engineering  
> Spring 2025–2026

![Python](https://img.shields.io/badge/Python_3.11+-3776AB?style=flat&logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/GPT--4o-412991?style=flat&logo=openai&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat&logo=langchain&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat&logo=langgraph&logoColor=white)
![LangFuse](https://img.shields.io/badge/LangFuse-000000?style=flat&logo=langfuse&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6F00?style=flat&logo=databricks&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic_v2-E92063?style=flat&logo=pydantic&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat&logo=numpy&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=flat&logo=jupyter&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat)
![Status](https://img.shields.io/badge/Status-Prototype_Complete-brightgreen?style=flat)

---

## Overview

Healthcare clinicians receive fragmented data from three disconnected sources: **Electronic Health Records (EHR)**, **Remote Patient Monitoring (RPM)** devices, and **Anamnesis** (patient self-reported history). When a monitoring alert fires, there is no system that instantly synthesizes all three into a coherent clinical picture.

ClinicalBridge is a proof-of-concept multi-agent system that closes this gap. Given an incoming RPM alert, it automatically retrieves relevant EHR history and patient-reported context, then synthesizes them into a structured **Clinical Context Brief (CCB)** — a clinician-readable summary that reduces time-to-decision from minutes to under 30 seconds.

---

## System Architecture

```
RPM Alert
    │
    ▼
┌─────────────────┐
│  Alert Triage   │  Classifies urgency (CRITICAL / URGENT / ROUTINE / INFORMATIONAL)
│     Agent       │  Formulates retrieval queries
└────────┬────────┘
         │
    ┌────┴────┐ parallel dispatch
    ▼         ▼
┌────────┐ ┌────────────┐
│  EHR   │ │ Anamnesis  │
│Retrieval│ │   Agent    │
│ Agent  │ │            │
└────┬───┘ └─────┬──────┘
     │           │
     └─────┬─────┘
           ▼
   ┌───────────────┐
   │  Synthesis    │  Produces the Clinical Context Brief
   │    Agent      │  with citations, confidence scores, uncertainty flags
   └───────┬───────┘
           ▼
   Clinical Context Brief
```

The **Orchestrator** is implemented as a **LangGraph `StateGraph`**: `triage → (CRITICAL ? escalate : EHR ∥ Anamnesis) → synthesis`. The EHR and Anamnesis nodes fan out from triage and run in parallel within a single super-step, then fan in at synthesis. It enforces safety guardrails (CRITICAL alerts escalate immediately, bypassing synthesis), and maintains a session audit log.

Every run is traced end-to-end with **LangFuse**: a single callback handler attached at the graph invocation propagates to all four agents, capturing each prompt, output, latency, and token usage as one trace tree. Runs are tagged with `patient_id`, `prompt_version`, and `scenario` metadata so the v1→v4 prompt iterations can be compared in the LangFuse dashboard. Tracing degrades gracefully — without `LANGFUSE_*` keys the system runs untraced.

---

## Clinical Context Brief Structure

Every run produces a structured CCB with six sections:

1. **Alert Summary** — what triggered the alert and its urgency classification
2. **Patient Snapshot** — demographics, active conditions, current medications
3. **Contextual Analysis** — how the alert relates to EHR history and patient-reported status
4. **Risk Assessment** — potential implications with confidence scores
5. **Recommended Actions** — suggested next steps, each with evidence citations
6. **Uncertainties & Gaps** — explicitly flagged missing data or conflicting information

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| LLM | OpenAI GPT-4o |
| Agent Framework | LangChain |
| Orchestration | LangGraph (StateGraph) |
| Observability | LangFuse (tracing) |
| Vector Store | ChromaDB |
| Data Validation | Pydantic v2 |
| Demo | Jupyter Notebooks |

---

## Project Structure

```
clinicalbridge/
├── main.py                   # Entry point: alert → CCB
├── agents/                   # 4 specialized LLM agents
├── orchestrator/             # Coordination, routing, safety guardrails
├── rag/                      # RAG pipeline: ingest, embed, retrieve
├── schemas/                  # Pydantic I/O contracts for all agents
├── prompts/                  # Versioned prompt files (v1–v4 per agent; v4 = final)
├── data/
│   ├── patients/             # Simulated EHR records (10–15 patients)
│   ├── rpm/                  # Simulated vital sign time-series
│   ├── anamnesis/            # Simulated patient self-reports
│   └── scenarios/            # 5 end-to-end test scenarios with gold-standard CCBs
├── evaluation/               # Metrics, evaluation harness, results
├── portfolio/                # Prompt iteration logs and failure analysis
└── notebooks/                # Demo walkthroughs (2+ scenarios end-to-end)
```

---

## Test Scenarios

Five clinical scenarios are designed to stress-test the system:

| # | Scenario | Key Challenge |
|---|---|---|
| 1 | Missed Medication | Anamnesis reveals stopped ACE inhibitor (cough side effect) not in EHR |
| 2 | False Alarm | Glucose alert is contextually benign given recent diet change + med adjustment |
| 3 | Silent Deterioration | Weight trend + patient-reported ankle swelling signals fluid retention |
| 4 | Incomplete Record | Sparse EHR from patient transfer — system must flag gaps explicitly |
| 5 | Conflicting Data | Patient claims full adherence; lab shows sub-therapeutic drug levels |

---

## Evaluation Targets

| Metric | Target |
|---|---|
| Triage urgency accuracy | ≥ 90% |
| EHR retrieval precision | ≥ 80% |
| EHR retrieval recall | ≥ 75% |
| Synthesis hallucination rate | ≤ 5% |
| End-to-end scenario pass rate | ≥ 4 / 5 |
| Time-to-brief (non-critical) | < 30 seconds |

---

## Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/ayhan-gurbangeldiyev/clinicalbridge-capstone.git
cd clinicalbridge-capstone

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your API credentials
cp .env.example .env
# Edit .env — choose ONE of the two options below:
```

**Option A — OpenAI API** (standard key from platform.openai.com):
```env
USE_AZURE=false
OPENAI_API_KEY=sk-...
```

**Option B — Azure OpenAI** (Azure for Students or enterprise):
```env
USE_AZURE=true
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your_key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

```bash
# 4. Generate the simulated RPM time-series
PYTHONPATH=. python data/rpm/generate_rpm.py

# 5. Ingest simulated EHR data into ChromaDB (idempotent)
PYTHONPATH=. python rag/ingest.py

# 6. Run a scenario (defaults to the final prompt version, v4)
PYTHONPATH=. python main.py --scenario missed_medication

# 7. Run all 5 evaluation scenarios (end-to-end + retrieval/completeness metrics)
PYTHONPATH=. python evaluation/harness.py v4

# 8. Agent-level qualitative metrics (LLM-as-judge)
PYTHONPATH=. python evaluation/judge.py

# 9. Demonstration notebooks (execute end-to-end with outputs)
PYTHONPATH=. jupyter nbconvert --to notebook --execute --inplace notebooks/03_demo_scenarios.ipynb
```

> **Final prompt version: v4** (trend-aware triage). Prompt history v1→v4 with iteration log
> and failure analyses (FA-001…005) is in `portfolio/`. The synthesis agent's per-call
> reasoning is logged to LangFuse with token usage and cost.

---

## Ethical Disclaimer

> **This is an educational prototype. It must never be used for actual clinical decision-making.**
>
> All patient data in this repository is entirely simulated and fictional. No real patient records were used at any stage. The system explicitly avoids making diagnoses — all outputs are contextual summaries intended to support, not replace, clinical judgment. A clinician must review every output before any action is taken.

---

## Course Module Coverage

| Module | Applied In |
|---|---|
| M1: Intro to LLMs | Model selection rationale, baseline prompt experiments |
| M2: Designing LLM Applications | Agent interface specs, architecture design |
| M3: Prompt Content | System prompts, few-shot examples, output schemas |
| M4: Conversational Agency | Anamnesis agent flow, synthesis reasoning chain |
| M5: Testing LLM Applications | Evaluation harness + LLM-as-judge (agent-level metrics), 5-scenario suite, LangFuse traces with token usage & cost |
| M6: Advanced LangChain | RAG pipeline, LangChain chains, structured output parsing |
| M7: Autonomous Agents | LangChain tools (`vector_store_search`, `alert_classification`, `rpm_trend`, `parse_anamnesis`) + per-patient entity memory |
| M8: Multi-Agent Systems | LangGraph StateGraph orchestration (parallel fan-out/fan-in), inter-agent communication, safety guardrails |
