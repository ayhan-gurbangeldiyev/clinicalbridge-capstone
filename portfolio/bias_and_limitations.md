# Bias Awareness & Limitations

Drop-in section for the report's Ethics chapter (Brief Ch. 12.2 "Bias awareness").

## Potential sources of bias

- **Simulated-data bias.** The 12-patient cohort was authored by hand and skews toward a
  few chronic conditions (hypertension, type 2 diabetes, heart failure). Demographics,
  comorbidity patterns, and writing style are not representative of a real population, so
  measured performance may not transfer to real clinical text with its abbreviations,
  inconsistencies, and missing fields.
- **Gold-standard bias.** Triage labels and gold retrieval chunks are author-defined. Any
  systematic error or preference in that labeling propagates directly into the reported
  accuracy and precision/recall numbers.
- **Prompt-design bias.** Few-shot examples encode the author's notion of "correct" triage
  and synthesis. The model may over-generalize from these examples (e.g., treating any
  glucose elevation like the worked example) rather than reasoning from first principles.
- **Model bias.** The underlying LLM (gpt-4o) carries the biases of its training data,
  including documented disparities in clinical reasoning across demographic groups. The
  system inherits these and adds no debiasing layer.
- **Retrieval/embedding bias.** The embedding model decides what counts as "relevant"
  context; concepts it separates poorly in vector space may be systematically under-
  retrieved, quietly shaping every downstream brief.

## How the design mitigates harm (not bias itself)

- Every claim must cite a source (`evidence_source`); unsupported claims are flagged, which
  limits fabricated bias-driven content (measured hallucination rate: 0%).
- Uncertainty and missing data are surfaced explicitly rather than smoothed over.
- Human-in-the-loop by design: the clinician makes every decision; CRITICAL alerts escalate
  without waiting for synthesis.

## What would be required before any real-world use

Demographic performance audits, validation on real (IRB-approved) records, a stronger
retrieval/validation layer, and prospective clinical evaluation — all explicitly out of
scope for this educational prototype.
