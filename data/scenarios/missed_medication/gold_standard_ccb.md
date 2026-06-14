# Gold Standard CCB — Scenario 1: Missed Medication

**Patient:** PT-001, Robert Harmon, 67M  
**Alert:** BP 188/112 — URGENT  
**Scenario:** Patient stopped Lisinopril ~4 weeks ago due to persistent dry cough (ACE inhibitor side effect). Has not informed provider.

---

## 1. Alert Summary
- **Triggered by:** Systolic BP 188.4 mmHg (+43 above upper threshold of 145), Diastolic 112.7 mmHg (+17.7 above threshold)
- **Urgency:** URGENT (not CRITICAL — no acute end-organ symptoms reported, but requires action within 1-2 hours)
- **Trend:** Progressive BP elevation over last 3 days consistent with medication discontinuation pattern

## 2. Patient Snapshot
- **Active conditions:** Essential hypertension (I10), Type 2 diabetes mellitus (E11.9)
- **Current medications (prescribed):** Lisinopril 10mg QD, Metformin 500mg BID
- **Key history:** Father had MI at 61; patient has T2DM as additional cardiovascular risk factor

## 3. Contextual Analysis
The RPM data shows a clear upward BP trend over the past 72 hours (from baseline ~138/88 to 188/112), consistent with abrupt antihypertensive discontinuation rather than chronic treatment failure. The anamnesis confirms the patient stopped Lisinopril approximately 4 weeks ago due to dry cough — a well-known ACE inhibitor class effect. The patient has not reported this to his provider. Glucose and weight remain within normal range, ruling out acute metabolic contribution to the BP elevation. The cough complaint is the clinical bridge between the alert and its root cause.

## 4. Risk Assessment
- **Primary risk:** Hypertensive urgency progressing to emergency if untreated; stroke risk elevated given family history (father MI at 61) and concurrent T2DM
- **Differential:** Medication non-adherence (most likely) vs. Lisinopril treatment failure vs. secondary hypertension (less likely given abrupt onset)
- **Confidence:** 0.88 — Root cause highly probable from EHR + anamnesis alignment; no conflicting data

## 5. Recommended Actions
1. **Contact patient within 2 hours** — Confirm medication status and cough symptom; rationale: anamnesis indicates patient is aware of cough but has not disclosed; a direct call may elicit honest disclosure. Evidence: anamnesis (medication_adherence), EHR visit note (lisinopril cough documented 2025-11-15)
2. **Switch from Lisinopril to ARB (e.g., Losartan)** — ACE inhibitor cough is a class effect; ARBs provide equivalent BP control without this side effect. Evidence: EHR visit note (cough complaint), anamnesis (stopped medication reason)
3. **Assess for end-organ involvement** — Ask about headache severity, visual changes, chest pain; if present, escalate to CRITICAL and refer to ED. Evidence: RPM alert level (URGENT), BP value 188/112
4. **Schedule in-person follow-up within 48 hours** — Re-check BP after resuming or switching medication. Evidence: RPM trend data

## 6. Uncertainties and Gaps
- **MISSING_DATA:** No refill records available to confirm last medication fill date
- **LOW_CONFIDENCE:** Exact duration of non-adherence uncertain (patient says "about two weeks" in anamnesis but RPM trend suggests 3+ days of acute worsening)
- **MISSING_DATA:** No recent lab data (last BMP was 2025-11-01) — potassium and creatinine relevant if switching to ARB

## 7. Immediate Review Required
**No** — URGENT classification; monitoring and outreach within 2 hours is appropriate. Escalate to CRITICAL if patient reports headache with visual disturbance, chest pain, or neurological symptoms.
