import asyncio
import json
from typing import Any, Dict, List

import httpx
from bs4 import BeautifulSoup


async def _fetch_searchapi(query: str, api_key: str, num: int, language: str) -> Dict[str, Any]:
    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": str(num),
        "hl": language or "ru",
        "gl": ("ru" if (language or "ru").startswith("ru") else "us"),
        "location": ("Russia" if (language or "ru").startswith("ru") else "United States"),
    }
    url = "https://www.searchapi.io/api/v1/search"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        # Prefer JSON; fall back to HTML parse if not JSON
        try:
            return resp.json()
        except json.JSONDecodeError:
            return {"html": resp.text}


def _parse_results(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    # JSON format from searchapi.io
    organic = payload.get("organic_results")
    if isinstance(organic, list):
        for r in organic:
            results.append({
                "title": r.get("title"),
                "link": r.get("link"),
                "snippet": r.get("snippet"),
                "source": r.get("source"),
            })
        if results:
            return results

    # HTML fallback: naive extraction of links with surrounding text
    html = payload.get("html")
    if isinstance(html, str) and html.strip():
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("a"):
            href = a.get("href")
            text = a.get_text(" ", strip=True)
            if href and text:
                results.append({
                    "title": text[:200],
                    "link": href,
                    "snippet": text[:300],
                    "source": None,
                })
            if len(results) >= 10:
                break

    return results


async def search_with_searchapi(query: str, api_key: str, num: int = 3, language: str = "ru") -> List[Dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        return []
    raw = await _fetch_searchapi(query=query, api_key=api_key, num=num, language=language)
    results = _parse_results(raw)
    # Limit to the requested number
    return results[:num]