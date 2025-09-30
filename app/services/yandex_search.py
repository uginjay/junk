from __future__ import annotations

from typing import List

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.models import EvidenceItem


YANDEX_XML_ENDPOINT = "https://yandex.ru/search/xml"


def _build_query_params(query: str) -> dict:
	settings = get_settings()
	if not settings.YANDEX_USER or not settings.YANDEX_KEY:
		raise ValueError("YANDEX_USER/YANDEX_KEY are required for Yandex XML Search")

	# Minimal set of params. For advanced controls, adjust if needed.
	params: dict = {
		"user": settings.YANDEX_USER,
		"key": settings.YANDEX_KEY,
		"query": query,
		"l10n": settings.YANDEX_L10N,
		"sortby": settings.YANDEX_SORTBY,
		"filter": settings.YANDEX_FILTER,
		# Limit number of results via groupby; typical Yandex XML convention
		# Example: "attr=d.mode=deep.groups-on-page=5.docs-in-group=1"
		"groupby": f"attr=d.mode=deep.groups-on-page={settings.YANDEX_RESULTS}.docs-in-group=1",
	}
	return params


def _extract_text(node) -> str:
	if node is None:
		return ""
	text = node.get_text(" ", strip=True)
	return " ".join(text.split())


def _parse_results(xml_text: str) -> List[EvidenceItem]:
	soup = BeautifulSoup(xml_text, "xml")
	items: List[EvidenceItem] = []
	for group in soup.find_all("group"):
		doc = group.find("doc")
		if doc is None:
			continue

		title = _extract_text(doc.find("title")) or _extract_text(doc.find("name"))
		url = _extract_text(doc.find("url"))
		if not url:
			# sometimes inside domains/domain + path
			domain = _extract_text(doc.find("domain"))
			if domain:
				url = f"https://{domain}"

		# snippets/passages vary; try several options
		passages = doc.find("passages") or doc.find("passage") or doc.find("headline")
		snippet = _extract_text(passages)

		if url:
			items.append(EvidenceItem(title=title or url, url=url, snippet=snippet))
	return items


def search_yandex_xml(query: str) -> List[EvidenceItem]:
	params = _build_query_params(query)
	with httpx.Client(timeout=20.0) as client:
		resp = client.get(YANDEX_XML_ENDPOINT, params=params)
		resp.raise_for_status()
		return _parse_results(resp.text)