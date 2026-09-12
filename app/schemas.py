from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["critical", "high", "medium", "low", "info"]


class Finding(BaseModel):
    severity: Severity
    category: str
    file: str
    line: int | None = None
    issue: str
    evidence: str
    recommendation: str


class SpecialistReport(BaseModel):
    agent: str
    summary: str
    findings: list[Finding] = Field(default_factory=list)


class TestSuggestion(BaseModel):
    name: str
    purpose: str
    edge_case: str


class PatchProposal(BaseModel):
    file: str
    explanation: str
    before: str
    after: str


class ReviewReport(BaseModel):
    score: int = Field(ge=0, le=100)
    summary: str
    confirmed_findings: list[Finding] = Field(default_factory=list)
    suggested_tests: list[TestSuggestion] = Field(default_factory=list)
    patch_proposals: list[PatchProposal] = Field(default_factory=list)
    quality_notes: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
