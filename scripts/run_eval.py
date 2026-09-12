import json
from pathlib import Path

from app.workflow import review_project
import asyncio


async def main():
    result = await review_project(Path("demo_project"))
    report = result["report"]

    print(f"Score: {report.score}/100")
    for finding in report.confirmed_findings:
        print(f"- {finding.severity}: {finding.category}: {finding.issue}")

    print("\nEvaluation cases:")
    for case in json.loads(Path("evals/cases.json").read_text()):
        print(f"- {case['name']} -> {case['expected_category']}")


if __name__ == "__main__":
    asyncio.run(main())
