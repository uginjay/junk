from __future__ import annotations

from typing import List

import httpx

from app.config import get_settings
from app.models import EvidenceItem


SEARCHAPI_ENDPOINT = "https://www.searchapi.io/api/v1/search"


def search_searchapi(query: str) -> List[EvidenceItem]:
	settings = get_settings()
	api_key = getattr(settings, "SEARCHAPI_KEY", None) or ""
	if not api_key:
		raise ValueError("SEARCHAPI_KEY is required for SearchAPI.io")

	# Using Google engine via SearchAPI.io as a default; can be adjusted to other engines
	params = {
		"engine": "google",
		"q": query,
		"num": getattr(settings, "SEARCHAPI_RESULTS", 5),
	}
	headers = {"Authorization": f"Bearer {api_key}"}

	with httpx.Client(timeout=20.0) as client:
		resp = client.get(SEARCHAPI_ENDPOINT, params=params, headers=headers)
		resp.raise_for_status()
		data = resp.json()

		items: List[EvidenceItem] = []
		organic = data.get("organic_results") or []
		for item in organic:
			title = item.get("title") or ""
			url = item.get("link") or ""
			snippet = item.get("snippet") or item.get("description") or ""
			if url:
				items.append(EvidenceItem(title=title or url, url=url, snippet=snippet))
		return items