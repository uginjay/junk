import os
import json
from typing import Any, Dict, List, Optional, Tuple

import requests
from flask import Flask, jsonify, render_template, request


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )

    @app.get("/")
    def index() -> Any:
        return render_template("index.html")

    @app.post("/api/factcheck")
    def factcheck() -> Any:
        payload = request.get_json(silent=True) or {}

        draft_text: str = payload.get("draft", "").strip()
        openai_api_key: str = payload.get("openai_api_key", "").strip()
        yandex_user: str = payload.get("yandex_user", "").strip()
        yandex_key: str = payload.get("yandex_key", "").strip()
        max_claims: int = int(payload.get("max_claims", 6))
        max_results_per_query: int = int(payload.get("max_results", 5))

        if not draft_text:
            return jsonify({"error": "draft is required"}), 400
        if not openai_api_key:
            return jsonify({"error": "openai_api_key is required"}), 400
        if not yandex_user or not yandex_key:
            return jsonify({"error": "yandex_user and yandex_key are required"}), 400

        try:
            claims = extract_claims_with_openai(
                openai_api_key=openai_api_key,
                draft_text=draft_text,
                max_claims=max_claims,
            )
        except Exception as exc:
            return (
                jsonify({"error": "Failed to extract claims", "details": str(exc)}),
                500,
            )

        enriched_claims: List[Dict[str, Any]] = []
        for claim in claims:
            search_queries: List[str] = claim.get("search_queries") or [claim.get("text", "")]  # type: ignore
            aggregated_results: List[Dict[str, Any]] = []
            seen_urls: set = set()

            for query in search_queries:
                try:
                    results = search_yandex_xml(
                        yandex_user=yandex_user,
                        yandex_key=yandex_key,
                        query=query,
                        max_results=max_results_per_query,
                    )
                except Exception as exc:
                    results = []

                for r in results:
                    url = r.get("url")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        aggregated_results.append(r)

            # Keep only top N evidence items (simple heuristic: already ranked by Yandex)
            top_evidence = aggregated_results[: max_results_per_query * 2]

            try:
                verdict = synthesize_verification(
                    openai_api_key=openai_api_key,
                    claim_text=claim.get("text", ""),
                    evidence_list=top_evidence,
                )
            except Exception as exc:
                verdict = {
                    "claim": claim.get("text", ""),
                    "verdict": "Uncertain",
                    "confidence": 0.2,
                    "rationale": f"Verification failed due to error: {exc}",
                    "citations": [],
                }

            enriched_claims.append(
                {
                    "id": claim.get("id"),
                    "text": claim.get("text"),
                    "search_queries": search_queries,
                    "evidence": top_evidence,
                    "fact_check": verdict,
                }
            )

        return jsonify(
            {
                "summary": summarize_report(enriched_claims),
                "claims": enriched_claims,
            }
        )

    return app


def extract_claims_with_openai(
    openai_api_key: str, draft_text: str, max_claims: int = 6
) -> List[Dict[str, Any]]:
    """Extract verifiable factual claims from a draft using OpenAI.

    Returns a list of dicts: {id, text, search_queries}
    """
    try:
        # Import locally to avoid hard dependency during import time
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeError(f"OpenAI SDK not available: {exc}")

    client = OpenAI(api_key=openai_api_key)

    system_prompt = (
        "You are a precise Russian fact-check assistant. Extract at most "
        f"{max_claims} short, concrete, verifiable factual claims from the given draft. "
        "Focus on dates, numbers, named entities, causal statements, rankings, and specific assertions. "
        "Output strictly in JSON with this schema: {\"claims\": [{\"id\": number, \"text\": string, \"search_queries\": [string, ...]}]} "
        "Keep claims concise (<= 25 words)."
    )

    user_prompt = (
        "Draft to analyze (Russian or multilingual):\n\n" + draft_text.strip()
    )

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = completion.choices[0].message.content or "{}"
    json_text = _extract_first_json_object(content)
    data = json.loads(json_text)
    raw_claims: List[Dict[str, Any]] = data.get("claims", [])

    claims: List[Dict[str, Any]] = []
    for idx, c in enumerate(raw_claims, start=1):
        text = (c.get("text") or "").strip()
        if not text:
            continue
        search_queries = c.get("search_queries") or [text]
        # normalize queries
        norm_queries = [q.strip() for q in search_queries if q and q.strip()]
        claims.append({"id": idx, "text": text, "search_queries": norm_queries})

    return claims[:max_claims]


def _extract_first_json_object(text: str) -> str:
    """Best-effort extraction of first JSON object from text."""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    # fallback minimal JSON
    return "{}"


def search_yandex_xml(
    yandex_user: str,
    yandex_key: str,
    query: str,
    max_results: int = 5,
    l10n: str = "ru",
) -> List[Dict[str, Any]]:
    """Query Yandex XML search and parse results.

    Requires Yandex.XML credentials (user, key).
    """
    params = {
        "user": yandex_user,
        "key": yandex_key,
        "query": query,
        "l10n": l10n,
        "sortby": "rlv",
        # Use deep grouping to get top N documents
        "groupby": f"attr=d.mode=deep.groups-on-page={max_results}.docs-in-group=1",
        # Do not filter duplicates; we will deduplicate by URL ourselves
        "filter": "none",
    }

    url = "https://yandex.ru/search/xml"
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()

    # Parse XML using xmltodict if available, otherwise fall back to ElementTree
    try:
        import xmltodict  # type: ignore
    except Exception:
        xmltodict = None  # type: ignore

    if xmltodict:
        parsed = xmltodict.parse(resp.text)
        return _extract_results_from_yandex_dict(parsed)
    else:
        # Minimal ElementTree fallback
        import xml.etree.ElementTree as ET

        tree = ET.fromstring(resp.text)
        # Very brittle fallback; prefer xmltodict. We'll search by tags.
        results: List[Dict[str, Any]] = []
        for doc in tree.findall('.//doc'):
            title_el = doc.find('title')
            url_el = doc.find('url')
            passage_el = doc.find('.//passage')
            results.append(
                {
                    "title": title_el.text if title_el is not None else "",
                    "url": url_el.text if url_el is not None else "",
                    "snippet": passage_el.text if passage_el is not None else "",
                    "source": "yandex.xml",
                }
            )
        return results[:max_results]


def _extract_results_from_yandex_dict(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract results from xmltodict-parsed Yandex XML response."""
    # Expected path: yandexsearch -> response -> results -> grouping -> group -> doc
    def to_list(x: Any) -> List[Any]:
        if x is None:
            return []
        if isinstance(x, list):
            return x
        return [x]

    root = parsed.get("yandexsearch", {})
    response = root.get("response", {})
    results = response.get("results", {})
    grouping = results.get("grouping", {})
    groups = to_list(grouping.get("group"))

    docs: List[Dict[str, Any]] = []
    for g in groups:
        doc = (g or {}).get("doc", {})
        title = (doc.get("title") or "").strip()
        url = (doc.get("url") or "").strip()
        passages = doc.get("passages") or {}
        passage = passages.get("passage") if isinstance(passages, dict) else None
        if isinstance(passage, list):
            snippet = " \u2022 ".join([p.strip() for p in passage if isinstance(p, str)])
        elif isinstance(passage, str):
            snippet = passage.strip()
        else:
            snippet = ""

        if url:
            docs.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "source": "yandex.xml",
                }
            )

    return docs


def synthesize_verification(
    openai_api_key: str,
    claim_text: str,
    evidence_list: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Use OpenAI to evaluate whether evidence supports or refutes the claim."""
    try:
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeError(f"OpenAI SDK not available: {exc}")

    client = OpenAI(api_key=openai_api_key)

    evidence_text_lines: List[str] = []
    for idx, ev in enumerate(evidence_list, start=1):
        title = ev.get("title") or ""
        url = ev.get("url") or ""
        snippet = ev.get("snippet") or ""
        evidence_text_lines.append(f"[{idx}] {title}\nURL: {url}\nSnippet: {snippet}")

    evidence_block = "\n\n".join(evidence_text_lines) if evidence_text_lines else "(no evidence)"

    system_prompt = (
        "You are a careful Russian fact-checker. Given a factual claim and web evidence, "
        "decide if the evidence overall SUPPORTS, REFUTES, or is UNCERTAIN. "
        "Consider reliability and recency. Output STRICT JSON: {\"claim\": str, \"verdict\": one of [Supported, Refuted, Uncertain], "
        "\"confidence\": number 0..1, \"rationale\": str (<= 100 words), \"citations\": [{\"title\": str, \"url\": str}]}."
    )

    user_prompt = (
        f"Claim:\n{claim_text}\n\nEvidence:\n{evidence_block}\n\nOutput JSON only."
    )

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = completion.choices[0].message.content or "{}"
    json_text = _extract_first_json_object(content)
    result = json.loads(json_text)

    # Basic normalization and guardrails
    verdict = result.get("verdict", "Uncertain")
    if verdict not in ("Supported", "Refuted", "Uncertain"):
        verdict = "Uncertain"
    confidence = result.get("confidence", 0.5)
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.5

    citations = result.get("citations") or []
    norm_citations: List[Dict[str, str]] = []
    for c in citations:
        title = (c.get("title") or "").strip()
        url = (c.get("url") or "").strip()
        if url:
            norm_citations.append({"title": title, "url": url})

    return {
        "claim": claim_text,
        "verdict": verdict,
        "confidence": max(0.0, min(1.0, confidence)),
        "rationale": (result.get("rationale") or "").strip(),
        "citations": norm_citations,
    }


def summarize_report(enriched_claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(enriched_claims)
    counts = {"Supported": 0, "Refuted": 0, "Uncertain": 0}
    for c in enriched_claims:
        v = ((c.get("fact_check") or {}).get("verdict") or "Uncertain")
        if v in counts:
            counts[v] += 1
        else:
            counts["Uncertain"] += 1
    return {"total_claims": total, **counts}


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)

