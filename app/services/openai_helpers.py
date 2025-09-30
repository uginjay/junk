from __future__ import annotations

import json
from typing import List, Tuple

from openai import OpenAI

from app.config import get_settings


def _get_client() -> OpenAI:
	settings = get_settings()
	if not settings.OPENAI_API_KEY:
		raise ValueError("OPENAI_API_KEY is required")
	return OpenAI(api_key=settings.OPENAI_API_KEY)


def extract_claims(text: str, max_claims: int) -> List[str]:
	settings = get_settings()
	client = _get_client()

	system_prompt = (
		"You are a precise assistant that extracts verifiable factual claims from Russian text. "
		"Return a JSON object with field 'claims' as a list of concise claims. "
		"Exclude opinions and vague statements. Make each claim atomic and testable."
	)
	user_prompt = (
		"Извлеки из следующего текста ключевые проверяемые факты/утверждения. "
		f"Максимум {max_claims}. Верни JSON с ключом 'claims'.\n\nТекст:\n" + text
	)

	resp = client.chat.completions.create(
		model=settings.OPENAI_MODEL_CLAIMS,
		messages=[
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_prompt},
		],
		temperature=0.2,
		response_format={"type": "json_object"},
	)

	content = resp.choices[0].message.content or "{}"
	try:
		data = json.loads(content)
		claims = data.get("claims", [])
		claims = [c.strip() for c in claims if isinstance(c, str) and c.strip()]
		return claims[:max_claims]
	except Exception:
		return []


def generate_verdict(claim: str, evidence: List[Tuple[str, str]]) -> dict:
	"""
	Given a claim and evidence tuples (snippet, url), produce verdict JSON with:
	- verdict: supported|refuted|uncertain
	- confidence: float 0..1
	- rationale: short Russian explanation
	- citations: list of urls
	"""
	settings = get_settings()
	client = _get_client()

	evidence_text = "\n\n".join([f"Источник: {u}\nФрагмент: {s}" for s, u in evidence]) or "Нет источников"

	system_prompt = (
		"You are a careful Russian fact-checker. Output JSON with fields: verdict, confidence, rationale, citations."
	)
	user_prompt = (
		f"Проверь утверждение: '{claim}'.\n\n"
		"Используй предоставленные выдержки из поисковой выдачи и ссылки как ориентиры. "
		"Если источники противоречивы или недостаточны — верни 'uncertain'. "
		"Верни JSON.\n\n"
		f"Данные:\n{evidence_text}"
	)

	resp = client.chat.completions.create(
		model=settings.OPENAI_MODEL_VERDICT,
		messages=[
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_prompt},
		],
		temperature=0.0,
		response_format={"type": "json_object"},
	)
	content = resp.choices[0].message.content or "{}"
	try:
		data = json.loads(content)
		verdict = str(data.get("verdict", "uncertain")).lower()
		if verdict not in {"supported", "refuted", "uncertain"}:
			verdict = "uncertain"
		confidence = float(data.get("confidence", 0.5))
		rationale = str(data.get("rationale", ""))
		citations = data.get("citations", [])
		if not isinstance(citations, list):
			citations = []
		citations = [str(u) for u in citations if isinstance(u, str)]
		return {
			"verdict": verdict,
			"confidence": max(0.0, min(1.0, confidence)),
			"rationale": rationale,
			"citations": citations,
		}
	except Exception:
		return {
			"verdict": "uncertain",
			"confidence": 0.5,
			"rationale": "Не удалось распарсить ответ модели",
			"citations": [],
		}