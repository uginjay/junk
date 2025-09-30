from __future__ import annotations

from typing import List

from app.models import ClaimResult, EvidenceItem, FactCheckReport
from app.services.openai_helpers import extract_claims, generate_verdict
from app.services.searchapi_search import search_searchapi


def factcheck_text(text: str, max_claims: int = 6) -> FactCheckReport:
	claims: List[str] = extract_claims(text, max_claims=max_claims)
	claim_results: List[ClaimResult] = []

	for claim in claims:
		# Run a targeted search query. Simple heuristic: quote the claim.
		query = f"\"{claim}\""
		evidence_items: List[EvidenceItem] = search_searchapi(query)

		# Prepare short evidence tuples for the model
		short_evidence = []
		for ev in evidence_items:
			short_snippet = ev.snippet[:500]
			short_evidence.append((short_snippet, ev.url))

		verdict_data = generate_verdict(claim, short_evidence)

		claim_results.append(
			ClaimResult(
				claim=claim,
				verdict=verdict_data["verdict"],
				confidence=verdict_data["confidence"],
				rationale=verdict_data["rationale"],
				citations=verdict_data["citations"],
				evidence=evidence_items,
			)
		)

	return FactCheckReport(original_text=text, claims=claim_results)