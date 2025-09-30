from __future__ import annotations

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.models import FactCheckRequest, FactCheckReport
from app.pipeline import factcheck_text

app = FastAPI(title="FactCheck Prototype")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
	return templates.TemplateResponse("index.html", {"request": request})


@app.post("/factcheck", response_class=HTMLResponse)
async def factcheck(request: Request, text: str = Form(...), max_claims: int = Form(6)):
	report: FactCheckReport = factcheck_text(text, max_claims=max_claims)
	return templates.TemplateResponse(
		"report.html",
		{"request": request, "report": report},
	)


@app.post("/api/factcheck")
async def factcheck_api(payload: FactCheckRequest) -> FactCheckReport:
	return factcheck_text(payload.text, max_claims=payload.max_claims)