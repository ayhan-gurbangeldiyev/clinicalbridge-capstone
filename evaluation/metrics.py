def triage_accuracy(predictions: list[str], gold_labels: list[str]) -> float:
    if not gold_labels:
        return 0.0
    correct = sum(p == g for p, g in zip(predictions, gold_labels))
    return correct / len(gold_labels)


def retrieval_precision(retrieved: list[str], relevant: list[str]) -> float:
    if not retrieved:
        return 0.0
    hits = sum(1 for c in retrieved if c in relevant)
    return hits / len(retrieved)


def retrieval_recall(retrieved: list[str], relevant: list[str]) -> float:
    if not relevant:
        return 1.0
    hits = sum(1 for c in relevant if c in retrieved)
    return hits / len(relevant)


def hallucination_rate(actions: list[dict]) -> float:
    if not actions:
        return 0.0
    unsupported = sum(
        1 for a in actions
        if not a.get("evidence_source") or a["evidence_source"].strip() == ""
    )
    return unsupported / len(actions)


def anamnesis_completeness(summary: dict) -> float:
    expected = ["chief_complaint", "recent_symptoms", "medication_adherence",
                "lifestyle_factors", "family_history", "patient_concerns"]
    filled = sum(
        1 for k in expected
        if summary.get(k) and summary[k] not in ("NOT_REPORTED", [], {})
    )
    return filled / len(expected)
