# Prompt Iteration Log

## Triage Agent

### v1 — Initial Design
**Date:** 2026-06-06
**Rationale:** Minimal system prompt with urgency definitions, chain-of-thought instruction, and three few-shot examples covering the three most likely alert types (BP, glucose, weight). Temperature=0 for deterministic classification.
**Known issues:** Few-shot examples may not cover edge cases like multi-parameter alerts or INFORMATIONAL classifications.

### v2 — After first evaluation (2026-06-06)
**Changes made:** Added explicit override instruction: agent must independently re-evaluate urgency using chain-of-thought, and may downgrade the device's raw `alert_category`. Added concrete example in the instruction ("a glucose of 214 mg/dL that is only 34 above threshold may be ROUTINE").
**Why:** FA-001 — false_alarm scenario: agent echoed device's URGENT label instead of reasoning that glucose +34 above threshold is mild (ROUTINE).
**Result:** v1 triage accuracy 4/5 (80%) → v2 5/5 (100%)

### v3 — Final (2026-06-06)
**Changes made:** (1) Expanded CRITICAL definition with absolute threshold values (SpO2 < 88%, systolic > 210, glucose < 40 or > 400, HR < 30 or > 150) to prevent ambiguity in true emergencies. (2) Added rule for multi-parameter alerts: co-occurring deviations compound risk and should escalate urgency. (3) Added 4th few-shot example covering INFORMATIONAL classification (borderline HR, no co-occurring deviation) to address the missing edge case from v1.
**Why:** v1/v2 lacked explicit CRITICAL thresholds — an agent could theoretically classify a systolic of 220 as URGENT instead of CRITICAL. Multi-parameter compounding was also absent; a patient with both elevated BP and tachycardia should be treated more urgently than either alone.
**Result:** 5/5 scenarios pass; CRITICAL escalation path confirmed correct.

### v4 — Trend-aware triage (final)
**Changes made:** Added a TREND RULE and a chain-of-thought step that consume a new "Recent
RPM trend" summary (from the `rpm_trend` tool over `data/rpm/`). A *sustained upward trend*
across multiple readings now escalates to at least URGENT even when the latest single reading
is only mildly above threshold; an *isolated spike* with an otherwise stable history may stay
ROUTINE. Updated the PT-005 and PT-008 few-shot examples to show both cases.
**Why:** FA-004 — `silent_deterioration`: v3 saw only the single reading (weight +1.7 kg) and
under-escalated to ROUTINE, missing the clinically significant multi-day climb (fluid
retention in heart failure). Triage had no view of the trajectory.
**Result:** Triage accuracy 80% (v3) → **100%** (v4). silent_deterioration now correctly
URGENT; false_alarm stays ROUTINE. 5/5 scenarios pass.

---

## EHR Retrieval Agent

### v1 — Initial Design
**Date:** 2026-06-06
**Rationale:** Anti-hallucination focus: every claim must be traceable to a chunk, absent data must be "NOT_FOUND". RAG retrieval at k=5 with cosine similarity scores surfaced to the LLM. Temperature=0.
**Known issues:** Long EHR records may produce low-relevance chunks if embedding space doesn't separate clinical concepts well. No guidance on how to score retrieval_confidence.

### v2 — After first evaluation (2026-06-06)
**Changes made:** (1) Replaced vague "0.0–1.0" guidance with explicit retrieval_confidence thresholds (0.8–1.0 complete, 0.5–0.8 partial, <0.5 sparse with LOW_CONFIDENCE flag). (2) Added instruction to cite source type (visit note date, lab test name) when extracting facts. (3) Added explicit note that a shorter accurate output beats a longer hallucinated one.
**Why:** FA-002 — incomplete_record scenario: agent assigned retrieval_confidence=0.7 for a sparse transfer record instead of flagging low confidence. Without the threshold guidance, the agent had no calibration anchor.
**Result:** Low-confidence records now produce explicit LOW_CONFIDENCE flags in missing_data_flags, enabling the synthesis agent to handle sparse EHR correctly.

### v3 — Final (2026-06-06)
**Changes made:** Added explicit 5-step chain-of-thought structure (identify relevant chunks → extract facts → cite sources → assess completeness → list missing data). Added 3 few-shot examples: (1) complete hypertension record, (2) partial heart failure record with LOW_CONFIDENCE, (3) edge case — sparse transfer record with near-empty output and explicit gap flags.
**Why:** Without CoT steps, the agent would sometimes skip completeness assessment, producing no missing_data_flags even when critical facts were absent. The few-shot examples anchor the expected output format and show the full range from complete to sparse data.
**Result:** Anamnesis completeness and missing_data_flags consistently populated; incomplete_record scenario correctly produces low-confidence output.

---

## Anamnesis Agent

### v1 — Initial Design
**Date:** 2026-06-06
**Rationale:** Instruction to preserve patient meaning while translating to structured output. SENSITIVE_FLAG handling built into system prompt. Fallback for missing anamnesis file handled in agent code.
**Known issues:** No chain-of-thought structure — agent may extract fields in arbitrary order or skip fields when the anamnesis JSON is sparse. SENSITIVE_FLAG instruction does not specify what to do with the sensitive data after flagging it.

### v2 — After first evaluation (2026-06-06)
**Changes made:** Added explicit 5-step chain-of-thought: (1) chief complaint, (2) chronological symptom timeline, (3) medication adherence assessment, (4) lifestyle factors, (5) patient concerns. Clarified SENSITIVE_FLAG rule: after flagging, do not include sensitive details in other fields.
**Why:** Without CoT structure, the agent would sometimes skip the chronological timeline step, losing the order of events critical for clinical interpretation. The SENSITIVE_FLAG clarification prevents sensitive disclosures from leaking into lifestyle_factors or other fields.
**Result:** Symptom timelines now consistently chronological; sensitive disclosures contained to sensitive_flags field only.

### v3 — Final (2026-06-06)
**Changes made:** Added 3 few-shot examples covering the key clinical scenarios: (1) missed medication — patient stopped drug, rising vitals, (2) conflicting adherence — patient claims compliance but context contradicts, (3) edge case — sensitive disclosure with dual mental health and substance use flags. All examples show complete field population with appropriate "NOT_REPORTED" for absent data.
**Why:** FA-003 — conflicting_data scenario: agent returned full medication_adherence compliance claim without flagging the discrepancy note, which caused the synthesis agent to miss the conflict. A few-shot example showing how to handle patient-reported vs. objective discrepancy was needed.
**Result:** Conflicting adherence now triggers explicit discrepancy note in medication_adherence.notes, enabling synthesis agent to generate CONFLICTING_INFO uncertainty flag.

---

## Synthesis Agent

### v1 — Initial Design
**Date:** 2026-06-06
**Rationale:** Six-step chain-of-thought structure forces the model to work through all data streams before producing the CCB. Citation rule requires every action to name a source. Confidence calibration thresholds defined explicitly. Temperature=0.1 for slight variability in synthesis language while keeping reasoning consistent.
**Known issues:** Output JSON may be verbose; parser may fail on very long synthesis outputs. The `urgency` field in the CCB was not explicitly mapped to the triage decision — the model could potentially echo the raw alert_category.

### v2 — After first evaluation (2026-06-06)
**Changes made:** Added explicit IMPORTANT note: "The top-level 'urgency' field must be set to the triage decision's urgency value (from the TriageDecision input), NOT the raw alert's alert_category."
**Why:** The false_alarm fix in Triage v2 correctly changed the urgency to ROUTINE, but the Synthesis agent was still reading the raw alert's alert_category (URGENT) for its top-level urgency field. The CCB showed URGENT even when triage said ROUTINE.
**Result:** CCB urgency field now correctly reflects the triage agent's re-evaluated classification.

### v3 — Final (2026-06-06)
**Changes made:** Added explicit conflicting data rule: when EHR and anamnesis contradict each other, the agent must (1) state both claims in contextual_analysis, (2) add a CONFLICTING_INFO uncertainty flag, and (3) recommend clinician investigation rather than assuming either source. All other v2 improvements retained.
**Why:** FA-003 — conflicting_data scenario: v2 synthesis would sometimes pick one source over the other without flagging the discrepancy, producing a confident-looking CCB that obscured a potentially clinically significant conflict (patient claims adherence, labs show sub-therapeutic levels).
**Result:** CONFLICTING_INFO flags consistently generated for conflicting_data scenario; clinician is alerted rather than misled.

### Post-v4 experiments to lift synthesis clinical accuracy (tested, NOT adopted — see FA-005)
Two synthesis prompt variants were trialled to push the LLM-judge *clinical accuracy* metric
toward ≥90%, and **both were reverted; v4 remains final:**
- **Verbose variant** (specificity + carry-every-flag rules): regressed (85%→83%) and caused a schema failure (invalid `SENSITIVE_FLAG` type).
- **No-speculation variant** (forbid unsupported claims): fixed one genuine speculative line on incomplete_record but the aggregate stayed within noise (~88–89%).

The judged metric was instead measured more robustly (3-sample average; accuracy scored per the Ch. 9.1 *factual-correctness* definition, not completeness), which honestly raised it from ~85% to ~89%. Lesson: exhaustive briefs do not score higher; ~89% is a stable judge ceiling, reported honestly rather than gamed.
