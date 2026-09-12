import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from agents import RunConfig, Runner, trace

from app.agents import (
    code_analyst,
    patch_engineer,
    quality_judge,
    security_reviewer,
    test_engineer,
)
from app.config import MODEL, TRACE_SENSITIVE_DATA
from app.context import ReviewContext
from app.schemas import ReviewReport, SpecialistReport


def _run_config() -> RunConfig:
    return RunConfig(
        workflow_name="RepoReviewer",
        trace_include_sensitive_data=TRACE_SENSITIVE_DATA,
        trace_metadata={
            "app": "RepoReviewer",
            "model": MODEL,
        },
    )


async def _run_specialist(agent, prompt: str, context: ReviewContext):
    result = await Runner.run(
        agent,
        prompt,
        context=context,
        max_turns=8,
        run_config=_run_config(),
    )
    return result.final_output


def _project_snapshot(root: Path) -> str:
    parts: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {
            ".py", ".md", ".txt", ".toml", ".yaml", ".yml", ".json"
        }:
            continue
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        parts.append(f"### {rel}\n```\n{text[:12000]}\n```")
    return "\n\n".join(parts)


def _serializable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [_serializable(v) for v in value]
    return value


async def review_project(root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    context = ReviewContext(root=root)
    snapshot = _project_snapshot(root)

    base_prompt = f"""
Review the uploaded project using your tools.

Project snapshot for cross-agent context:
{snapshot}

Important: the snapshot may be truncated. Use the tools to inspect files directly.
"""

    with trace("RepoReviewer workflow"):
        specialist_results = await asyncio.gather(
            _run_specialist(code_analyst, base_prompt, context),
            _run_specialist(security_reviewer, base_prompt, context),
            _run_specialist(test_engineer, base_prompt, context),
        )

        reports = [
            r if isinstance(r, SpecialistReport) else SpecialistReport.model_validate(r)
            for r in specialist_results
        ]

        findings_text = json.dumps(
            [_serializable(report) for report in reports],
            indent=2,
        )

        patch_prompt = f"""
Project source:
{snapshot}

Specialist findings:
{findings_text}

Create minimal, evidence-backed before/after patch proposals for the
highest-value issues. Return no more than 5 proposals.
"""
        patch_result = await Runner.run(
            patch_engineer,
            patch_prompt,
            context=context,
            max_turns=5,
            run_config=_run_config(),
        )
        patches = patch_result.final_output
        if not isinstance(patches, list):
            patches = [patches]

        judge_prompt = f"""
PROJECT:
{snapshot}

SPECIALIST REPORTS:
{findings_text}

PATCH PROPOSALS:
{json.dumps(_serializable(patches), indent=2)}

Build the final ReviewReport.
"""
        judge_result = await Runner.run(
            quality_judge,
            judge_prompt,
            context=context,
            max_turns=5,
            run_config=_run_config(),
        )
        report = judge_result.final_output
        if not isinstance(report, ReviewReport):
            report = ReviewReport.model_validate(report)

    elapsed = round(time.perf_counter() - started, 2)

    return {
        "report": report,
        "specialists": reports,
        "patches": patches,
        "metadata": {
            "model": MODEL,
            "elapsed_seconds": elapsed,
            "agents": [
                "Code Analyst",
                "Security Reviewer",
                "Test Engineer",
                "Patch Engineer",
                "Quality Judge",
            ],
            "architecture": "parallel specialists -> patch engineer -> quality judge",
            "trace_sensitive_data": TRACE_SENSITIVE_DATA,
        },
    }
