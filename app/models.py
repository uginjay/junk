from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
	title: str = Field(default="")
	url: str
	snippet: str = Field(default="")


class ClaimResult(BaseModel):
	claim: str
	verdict: Literal["supported", "refuted", "uncertain"]
	confidence: float = Field(ge=0.0, le=1.0)
	rationale: str
	citations: List[str] = Field(default_factory=list)
	evidence: List[EvidenceItem] = Field(default_factory=list)


class FactCheckRequest(BaseModel):
	text: str
	max_claims: int = Field(default=6, ge=1, le=12)


class FactCheckReport(BaseModel):
	original_text: str
	claims: List[ClaimResult]
	summary: Optional[str] = None