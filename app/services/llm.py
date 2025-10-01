import json
import os
from typing import Any, Dict, List

from openai import OpenAI


class LLMClient:
    def __init__(self, model_extract: str = "gpt-4o-mini", model_judge: str = "gpt-4o-mini") -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=api_key)
        self.model_extract = model_extract
        self.model_judge = model_judge

    def extract_claims(self, text: str, max_claims: int = 5, language: str = "ru") -> Dict[str, Any]:
        system_prompt = (
            "You are a precise fact-check planning assistant. "
            "Extract up to N check-worthy factual claims from the user's draft. "
            "Return concise atomic claims that could be verified on the web. "
            "For each claim, propose a short search query. "
            "Respond in JSON with a 'claims' array."
        )
        user_prompt = (
            f"Language: {language}\n"
            f"MaxClaims: {max_claims}\n\n"
            "Draft text to analyze:\n" + text.strip()
        )

        response = self.client.chat.completions.create(
            model=self.model_extract,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Extract up to the requested number (N) of claims. "
                        "Schema: {\n  \"claims\": [ { \"id\": string, \"statement\": string, \"query\": string } ]\n}\n\n"
                        + user_prompt
                    ),
                },
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
        except Exception:
            data = {"claims": []}

        # Normalize and trim list size
        claims: List[Dict[str, Any]] = []
        for idx, c in enumerate(data.get("claims", [])[:max_claims]):
            statement = str(c.get("statement", "")).strip()
            if not statement:
                continue
            query = str(c.get("query") or statement)[:200]
            claims.append({
                "id": str(c.get("id") or f"c{idx+1}"),
                "statement": statement,
                "query": query,
            })
        return {"claims": claims}

    def judge_claim(self, statement: str, evidence: List[Dict[str, Any]], language: str = "ru") -> Dict[str, Any]:
        evidence_lines: List[str] = []
        for i, item in enumerate(evidence[:5]):
            title = str(item.get("title") or "").strip()
            snippet = str(item.get("snippet") or "").strip()
            url = str(item.get("link") or item.get("url") or "").strip()
            host = str(item.get("source") or "").strip()
            evidence_lines.append(f"[{i}] {title}\n{snippet}\n{url} {('(' + host + ')') if host else ''}")
        evidence_text = "\n\n".join(evidence_lines) if evidence_lines else "(no evidence available)"

        system_prompt = (
            "You are a careful fact-checker. Given a claim and web snippets, "
            "decide whether the claim is supported, refuted, or unclear. "
            "Use only the provided evidence. Return JSON with keys: verdict(supported|refuted|unclear), "
            "confidence(0..1), rationale(short), citations([indexes])."
        )
        user_prompt = (
            f"Language: {language}\n"
            f"Claim: {statement}\n\n"
            f"Evidence:\n{evidence_text}"
        )

        response = self.client.chat.completions.create(
            model=self.model_judge,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        content = response.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
        except Exception:
            data = {
                "verdict": "unclear",
                "confidence": 0.0,
                "rationale": "Model returned non-JSON output.",
                "citations": [],
            }

        verdict = str(data.get("verdict") or "unclear").lower()
        if verdict not in ("supported", "refuted", "unclear"):
            verdict = "unclear"
        confidence = data.get("confidence")
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.0
        citations = data.get("citations") or []
        if not isinstance(citations, list):
            citations = []

        return {
            "verdict": verdict,
            "confidence": max(0.0, min(1.0, confidence)),
            "rationale": str(data.get("rationale") or ""),
            "citations": citations,
        }