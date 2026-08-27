# RepoReviewer

RepoReviewer is a small multi-agent Python application that performs code review,
test analysis, static analysis and safe patch proposals.

## Architecture

```text
Streamlit UI
     |
     v
Workflow
     |
     +--> Code Analyst --------+
     +--> Security Reviewer ---+--> Patch Engineer --> Quality Judge
     +--> Test Engineer -------+
                |
                +--> Ruff
```

## Why this architecture?

Specialists run in parallel to reduce latency and keep responsibilities narrow.
The Patch Engineer proposes changes but never modifies the repository.
The Quality Judge is a final quality gate that removes duplicated or unsupported
findings.

Deterministic tooling is used for deterministic evidence: Ruff performs static
analysis. The LLM handles interpretation, prioritization and test design.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# add OPENAI_API_KEY to .env

streamlit run streamlit_app.py
```

Open the local Streamlit URL and click **Run agentic review**.

## Observability

The OpenAI Agents SDK has built-in tracing. Review the trace in the OpenAI
dashboard after a run.

## Security boundary

This demo intentionally does not execute uploaded Python. It reads source files
and runs Ruff only. Do not add arbitrary shell or test execution to a public
deployment without an isolated sandbox.

## Evaluation

`evals/cases.json` contains small regression cases. The current evaluation script
is intentionally lightweight; a production version should run a larger golden
dataset and measure precision, recall, false-positive rate, severity accuracy,
latency and token cost.
