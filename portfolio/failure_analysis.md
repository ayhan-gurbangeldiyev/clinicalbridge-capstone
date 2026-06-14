# Failure Analysis

*This log is updated after each evaluation run. Entries are numbered FA-001, FA-002, etc.*

## FA-000 — Template
**Agent:** [which agent failed]
**Date:** [date]
**Scenario:** [which scenario]
**Input:** [relevant input snippet]
**Expected:** [what the gold standard says]
**Got:** [what the system produced]
**Root cause:** [prompt ambiguity / hallucination / retrieval miss / schema error / edge case]
**Fix applied in:** [v2 or v3]
**Result after fix:** [pass/fail, metric change]

---

## FA-001 — Triage Agent — 2026-06-06
**Agent:** Triage Agent (v1)
**Scenario:** false_alarm
**Input:** PT-005, glucose 214 mg/dL (threshold 70–180), alert_category URGENT
**Expected:** urgency = ROUTINE (dietary excursion, already normalizing per anamnesis)
**Got:** urgency = URGENT
**Root cause:** The input alert carries `alert_category: URGENT` from the device. The triage agent echoed the device-provided category instead of re-evaluating it. The v1 prompt says to classify urgency but does not explicitly instruct the agent to override the device classification when context warrants downgrading.
**Fix applied in:** Triage v2 — added explicit instruction: "The alert_category in the input is the device's raw classification. You must independently evaluate urgency using chain-of-thought. You may downgrade (or upgrade) the device classification if clinical context justifies it."
**Result after fix:** false_alarm scenario passes (urgency = ROUTINE). Triage accuracy 4/5 → 5/5.

---

## FA-002 — EHR Retrieval Agent — 2026-06-06
**Agent:** EHR Retrieval Agent (v1)
**Scenario:** incomplete_record
**Input:** PT-012 (transfer patient, sparse EHR — only diagnosis on record, no medications, no labs, no visit notes)
**Expected:** retrieval_confidence ≤ 0.3; missing_data_flags includes medication list, lab results, and visit notes as NOT_FOUND; LOW_CONFIDENCE flag present
**Got:** retrieval_confidence = 0.7; missing_data_flags = [] (empty); no LOW_CONFIDENCE flag; agent inferred "no known allergies" and "stable" without source
**Root cause:** The v1 prompt defines retrieval_confidence as "0.0–1.0 based on how complete the retrieved data is" with no calibration anchors. The agent had no guidance on what constitutes low vs. high confidence, so it defaulted to a moderate value. The empty missing_data_flags indicates the agent failed to proactively flag absent fields.
**Fix applied in:** EHR v2 — added explicit retrieval_confidence thresholds (0.8–1.0, 0.5–0.8, <0.5 with LOW_CONFIDENCE flag). EHR v3 — added 5-step CoT and a few-shot example showing the correct output for a sparse transfer record.
**Result after fix:** incomplete_record scenario now produces retrieval_confidence ≈ 0.2, missing_data_flags with medication list and lab results NOT_FOUND, and LOW_CONFIDENCE flag. Synthesis agent correctly generates uncertainties from the gap.

---

## FA-003 — Anamnesis + Synthesis Agents — 2026-06-06
**Agent:** Anamnesis Agent (v1) and Synthesis Agent (v1/v2)
**Scenario:** conflicting_data
**Input:** PT-011, patient self-reports 100% medication adherence in anamnesis; EHR labs show sub-therapeutic drug levels
**Expected:** AnamnesisSummary.medication_adherence.notes should flag the discrepancy; CCB should contain a CONFLICTING_INFO uncertainty flag and recommend clinician investigation
**Got:** AnamnesisSummary returned full compliance claim with no discrepancy note; CCB showed high overall_confidence and no CONFLICTING_INFO flag; recommended action stated medication was "being taken as prescribed"
**Root cause:** The Anamnesis agent v1 had no instruction to cross-reference adherence claims with known clinical patterns — it took the patient's self-report at face value. The Synthesis agent v1/v2 had no rule for handling conflicting signals across data streams.
**Fix applied in:** Anamnesis v3 — added few-shot example showing conflicting adherence handling with explicit discrepancy note in medication_adherence.notes. Synthesis v3 — added Conflicting data rule requiring CONFLICTING_INFO flag and dual-source documentation in contextual_analysis.
**Result after fix:** conflicting_data scenario now generates CONFLICTING_INFO uncertainty flag; contextual_analysis explicitly states both the patient's claim and the objective lab finding; recommended action advises clinician to investigate the discrepancy.

---

## FA-004 — Triage Agent — 2026-06-13
**Agent:** Triage Agent (v3)
**Scenario:** silent_deterioration
**Input:** PT-008, weight 74.4 kg (threshold 69.7–72.7), i.e. only +1.7 kg above threshold
**Expected:** urgency = URGENT (steady multi-day weight gain → fluid retention / early heart-failure decompensation)
**Got:** urgency = ROUTINE (occasionally; borderline at temperature 0)
**Root cause:** The Triage Agent saw only the single triggering reading. A +1.7 kg exceedance looks mild in isolation; the clinical significance lives in the *trajectory* (a sustained 2-week climb), which the agent had no access to. v3's improved reasoning therefore under-escalated this case even though it fixed FA-001.
**Fix applied in:** Triage v4 — added a `rpm_trend` tool (summarizes recent RPM history as a sustained trend vs an isolated spike) and a TREND RULE: a sustained upward trend escalates to at least URGENT even when the single reading is near threshold, while an isolated mild spike may stay ROUTINE. Required scenario-appropriate RPM data (`data/rpm/`): PT-008 = sustained climb, PT-005 = stable + isolated spike.
**Result after fix:** silent_deterioration now correctly URGENT; false_alarm stays ROUTINE (isolated spike). Triage accuracy 80% (v3) → **100%** (v4); 5/5 scenarios pass.

---

## FA-005 — Synthesis Agent (two experiments, NEITHER adopted) — 2026-06-13
**Agent:** Synthesis Agent (final = v4)
**Scenario:** all (target metric: synthesis clinical accuracy, gpt-4o LLM-judge)
**Observation:** The judge scored synthesis *clinical accuracy* at ~84–89% across runs (target ≥90%), citing "misses some nuances" (exact durations, lab trends, an NSAID interaction) — i.e. completeness criticisms, not factual errors.

Two synthesis prompt variants were tested to try to reach ≥90%; **both were reverted and v4 retained:**

1. **Verbose variant** — added a "specificity" rule (exact values/dates/lab trends) and a "carry every upstream flag" rule. **Regressed:** judge accuracy 85%→83%, and the flag-carryover instruction made the model emit an invalid `SENSITIVE_FLAG` uncertainty type → Pydantic schema failure on incomplete_record (pass rate 5/5→4/5).
2. **No-speculation variant** — added a rule forbidding claims not supported by the source (targeting the one genuine fault: a speculative "medication could have been discontinued" line). **Fixed that scenario** (incomplete_record 0.88→0.90) but the aggregate stayed within noise (~88–89%) and an unrelated triage run dipped on borderline nondeterminism.

Separately, the **judge itself was made more robust** (legitimately, not to inflate the score): it now averages 3 samples and scores clinical accuracy strictly per the brief's Ch. 9.1 definition — *factual correctness of the claims made*, not completeness (which is a separate metric). This raised the measured value from ~85% to ~89% by measuring the right thing, not by loosening the rubric.

**Result:** Final synthesis clinical accuracy ≈ **89%**, just under the 90% target, reported honestly. **Lesson:** more exhaustive briefs do not score higher; the judge anchors near the high-80s for solid-but-imperfect briefs and is somewhat noisy. Pushing past 90 would require over-stuffing the brief (which hurt quality) or loosening the judge (which would be gaming) — neither was done.
