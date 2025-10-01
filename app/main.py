import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from app.services.llm import LLMClient
from app.services.search import search_with_searchapi


load_dotenv()

app = FastAPI(title="FactCheck Prototype")

# Serve static assets from /assets and index from /
PUBLIC_DIR = "/workspace/public"
app.mount("/assets", StaticFiles(directory=PUBLIC_DIR), name="assets")


class FactCheckRequest(BaseModel):
    text: str
    language: Optional[str] = "ru"
    max_claims: Optional[int] = 5
    max_results_per_claim: Optional[int] = 3


@app.get("/")
async def root_index() -> Any:
    index_path = os.path.join(PUBLIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


@app.post("/api/factcheck")
async def factcheck(req: FactCheckRequest) -> Dict[str, Any]:
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    searchapi_key = os.getenv("SEARCHAPI_API_KEY")
    if not searchapi_key:
        raise HTTPException(status_code=500, detail="SEARCHAPI_API_KEY is not set")

    llm = LLMClient()

    # 1) Extract check-worthy claims
    try:
        extraction = llm.extract_claims(
            text=req.text,
            max_claims=req.max_claims or 5,
            language=req.language or "ru",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM extraction failed: {e}")

    claims: List[Dict[str, Any]] = extraction.get("claims", [])
    if not claims:
        return {
            "claims": [],
            "report": [],
            "notes": "No check-worthy claims found by the LLM."
        }

    # 2) Search evidence with searchapi.io
    try:
        for claim in claims:
            query = claim.get("query") or claim.get("statement")
            results = await search_with_searchapi(
                query=query,
                api_key=searchapi_key,
                num=req.max_results_per_claim or 3,
                language=req.language or "ru",
            )
            claim["evidence"] = results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    # 3) Judge each claim using LLM with gathered evidence
    report: List[Dict[str, Any]] = []
    for claim in claims:
        try:
            judgment = llm.judge_claim(
                statement=claim.get("statement", ""),
                evidence=claim.get("evidence", []),
                language=req.language or "ru",
            )
        except Exception as e:
            judgment = {
                "verdict": "unclear",
                "confidence": 0.0,
                "rationale": f"Judgment failed: {e}",
                "citations": []
            }
        report.append({
            "id": claim.get("id"),
            "statement": claim.get("statement"),
            "judgment": judgment,
            "evidence": claim.get("evidence", []),
        })

    return {"claims": claims, "report": report}