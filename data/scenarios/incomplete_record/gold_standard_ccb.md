# Gold Standard CCB — Scenario 4: Incomplete Record

**Patient:** PT-012, Amara Diallo, 52F  
**Alert:** BP 172/106 — URGENT  
**Scenario:** New transfer patient with sparse EHR, unknown prior medications, possible duplicate antihypertensive therapy. Clinical decision-making is severely limited by information gaps.

---

## 1. Alert Summary
- **Triggered by:** Systolic BP 172.6 mmHg (+22.6 above upper threshold of 150), Diastolic 106.3 mmHg (+11.3 above threshold)
- **Urgency:** URGENT — BP significantly elevated; limited ability to contextualize without complete medication history
- **Trend:** BP has been persistently elevated since enrollment (RPM shows +20 mmHg offset throughout), suggesting chronic undertreatment rather than acute event

## 2. Patient Snapshot
- **Active conditions:** Essential hypertension (I10), Personal history of nicotine dependence (Z87.891)
- **Current medications:** Amlodipine 5mg QD (prescribed at first visit 2025-11-10) + Unknown antihypertensive from overseas (name unknown, label in French, dose unknown)
- **Key history:** New transfer from overseas; no records available; may be taking two antihypertensives simultaneously; allergy to unknown antibiotic

## 3. Contextual Analysis
This alert cannot be fully interpreted without critical missing information. The patient has been on Amlodipine 5mg empirically prescribed at her first visit, but is also continuing an unidentified medication from her home country. The anamnesis identifies this as a possible CCB or ACEI/ARB from a French-speaking country, creating a risk of duplicate antihypertensive therapy or drug-drug interaction. Despite this, her BP remains persistently high (172/106), suggesting either the current regimen is inadequate or the overseas medication has been discontinued. Language barrier and recent immigration add complexity. The allergy history (unknown antibiotic reaction) is an additional safety concern for any new prescriptions.

## 4. Risk Assessment
- **Primary risk:** Sustained uncontrolled hypertension (chronic cardiovascular risk accumulation); secondary risk of adverse drug event from unidentified medication combination
- **Differential:** Inadequate treatment (most likely) vs. medication non-adherence vs. white coat effect (less likely given RPM data) vs. secondary hypertension (cannot exclude without labs)
- **Confidence:** 0.45 — Confidence is intentionally low; insufficient data to draw strong conclusions

## 5. Recommended Actions
1. **Urgent medication reconciliation** — Patient should bring overseas medication bottle to next visit; consider pharmacy identification services or poison control for French-label medication identification. Evidence: anamnesis (overseas medication, French label), EHR first visit note
2. **Order baseline labs immediately** — BMP (renal function, electrolytes), lipid panel, urinalysis for proteinuria; these are overdue for a new hypertension patient and will guide treatment decisions. Evidence: EHR (labs empty, first visit note ordered baseline labs but results not in chart)
3. **Schedule urgent visit within 48 hours with interpreter** — Anamnesis documents language barrier; interpreter services essential for accurate history and medication reconciliation. Evidence: anamnesis (LANGUAGE_BARRIER flag)
4. **Hold Amlodipine dose increase until medication identity confirmed** — Risk of additive hypotension if overseas medication is also a CCB or ACEI. Evidence: anamnesis (POSSIBLE_DUPLICATE_MEDICATION flag)

## 6. Uncertainties and Gaps
- **MISSING_DATA:** Identity, dose, and mechanism of overseas medication — highest priority gap
- **MISSING_DATA:** No baseline labs (renal function, lipid panel) — cannot safely titrate antihypertensives
- **MISSING_DATA:** No prior medical records from overseas treating physician
- **MISSING_DATA:** Nature of prior antibiotic allergy — limits future prescribing options
- **CONFLICTING_INFO:** Prescribed one antihypertensive at first visit while patient continues unknown second antihypertensive — potential duplicate therapy unresolved

## 7. Immediate Review Required
**No** — URGENT but chronic in nature; no acute end-organ emergency. Priority: medication reconciliation and lab workup within 48 hours.
