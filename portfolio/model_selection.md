# Model Selection Rationale

## Primary LLM — GPT-4o

**Selected:** OpenAI GPT-4o  
**Considered:** GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo

### Why GPT-4o

Clinical reasoning requires the ability to synthesize heterogeneous information (structured JSON, clinical notes, lab values) and apply domain knowledge to produce safe, well-calibrated outputs. GPT-4o was selected because:

1. **Instruction following:** GPT-4o reliably follows multi-step chain-of-thought instructions and complex output schemas (Pydantic-enforced JSON) without frequent parsing failures. GPT-3.5-turbo and GPT-4o-mini struggled with the 6-step synthesis CoT and produced schema violations at a higher rate in baseline experiments.

2. **Clinical vocabulary:** GPT-4o correctly interprets ICD-10 codes, drug names, lab abbreviations (BNP, HbA1c, BMP), and clinical urgency terms without hallucinating plausible-sounding but incorrect values.

3. **Calibrated uncertainty:** GPT-4o more consistently expresses uncertainty through confidence scores and missing_data_flags rather than filling gaps with confident-sounding fabrications.

### Rejected Alternatives

| Model | Why Rejected |
|---|---|
| GPT-4o-mini | Schema compliance failures in synthesis agent (~20% parse errors in baseline); weaker clinical reasoning on silent_deterioration scenario |
| GPT-4-turbo | Higher cost, no meaningful quality improvement over GPT-4o for this task; slower response time |
| GPT-3.5-turbo | Frequent hallucination in EHR extraction; urgency misclassification on 3/5 baseline scenarios |

---

## Temperature Settings

| Agent | Temperature | Rationale |
|---|---|---|
| Triage | 0.0 | Deterministic classification — same alert must always produce the same urgency level |
| EHR Retrieval | 0.0 | Fact extraction — output must be traceable to source; variability introduces hallucination risk |
| Anamnesis | 0.0 | Structured extraction from a fixed input — no benefit to variability |
| Synthesis | 0.1 | Slight variability improves the naturalness of the contextual_analysis narrative without affecting structured fields |

---

## Embedding Model — text-embedding-3-small

**Selected:** `text-embedding-3-small`  
**Considered:** `text-embedding-3-large`, `text-embedding-ada-002`

### Why text-embedding-3-small

- **Sufficient semantic separation:** Clinical EHR text contains domain-specific terms that are well-separated by text-embedding-3-small in practice. Cosine similarity scores differentiate hypertension records from heart failure records with >0.3 margin in cross-patient tests.
- **Cost efficiency:** text-embedding-3-small costs ~20× less per token than text-embedding-3-large. For a prototype ingesting 12 patients × multiple chunks, this is significant.
- **Speed:** Faster embedding generation during ingest; critical for batch ingest of full patient cohort.

### ada-002 Comparison

`text-embedding-ada-002` is the previous generation. text-embedding-3-small outperforms ada-002 on MTEB benchmarks while costing less, making ada-002 a strictly dominated option.

---

## Chunking Strategy

| Parameter | Value | Rationale |
|---|---|---|
| Chunk size | 512 chars | Balances context window cost against retrieval granularity; a single SOAP note fits in 1–2 chunks |
| Overlap | 64 chars | Prevents sentences split across chunk boundaries from being lost in retrieval |
| Retrieval k | 5 | Empirically sufficient to surface relevant medications, labs, and visit notes without flooding the LLM context |

---

## Baseline Prompt Experiments (M1 Evidence)

Three prompt strategies were evaluated on the missed_medication scenario before settling on the final architecture:

| Strategy | Result |
|---|---|
| Single monolithic prompt (all 4 agent roles combined) | Synthesis agent dominated; EHR facts frequently hallucinated |
| Chain of agents with no CoT | Triage accuracy 60%; synthesis produced generic output without source citations |
| Specialized agents with explicit CoT (final design) | Triage accuracy 100%; synthesis citations present in all 5 scenarios |

The specialized multi-agent design with per-agent CoT instructions was clearly superior, validating the architectural choice described in the system design.
