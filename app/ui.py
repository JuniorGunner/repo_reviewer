import asyncio
import json
import os
import tempfile
from pathlib import Path

import streamlit as st

from app.config import ALLOWED_EXTENSIONS, MAX_FILE_BYTES, MAX_FILES, MAX_TOTAL_BYTES
from app.workflow import review_project


def _save_uploads(uploaded_files) -> Path:
    if len(uploaded_files) > MAX_FILES:
        raise ValueError(f"Maximum {MAX_FILES} files allowed.")

    total = 0
    temp_dir = Path(tempfile.mkdtemp(prefix="repo_reviewer_"))

    for uploaded in uploaded_files:
        name = Path(uploaded.name)
        if name.is_absolute() or ".." in name.parts:
            raise ValueError(f"Unsafe filename: {uploaded.name}")

        suffix = name.suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            continue

        data = uploaded.getvalue()
        if len(data) > MAX_FILE_BYTES:
            raise ValueError(f"{uploaded.name} exceeds the per-file size limit.")

        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise ValueError("Uploaded project exceeds the total size limit.")

        destination = temp_dir / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

    if not any(temp_dir.rglob("*")):
        raise ValueError("No supported source files were uploaded.")

    return temp_dir


def _load_demo() -> Path:
    return Path(__file__).resolve().parent.parent / "demo_project"


def _render_report(result: dict):
    report = result["report"]
    meta = result["metadata"]

    st.success("Review complete")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quality score", f"{report.score}/100")
    c2.metric("Confirmed findings", len(report.confirmed_findings))
    c3.metric("Test suggestions", len(report.suggested_tests))
    c4.metric("Runtime", f'{meta["elapsed_seconds"]}s')

    st.markdown("### Executive summary")
    st.write(report.summary)

    tabs = st.tabs(["Findings", "Suggested tests", "Patches", "Workflow"])

    with tabs[0]:
        if not report.confirmed_findings:
            st.info("No high-confidence findings.")
        for finding in report.confirmed_findings:
            icon = {
                "critical": "🚨",
                "high": "🔴",
                "medium": "🟠",
                "low": "🟡",
                "info": "🔵",
            }[finding.severity]
            with st.expander(
                f"{icon} {finding.severity.upper()} — {finding.category} — {finding.file}"
            ):
                if finding.line:
                    st.caption(f"Line {finding.line}")
                st.write(finding.issue)
                st.code(finding.evidence, language="python")
                st.markdown(f"**Recommendation:** {finding.recommendation}")

    with tabs[1]:
        for test in report.suggested_tests:
            st.markdown(f"**`{test.name}`**")
            st.write(test.purpose)
            st.caption(f"Edge case: {test.edge_case}")

    with tabs[2]:
        if not report.patch_proposals:
            st.info("No patch proposals survived the quality gate.")
        for patch in report.patch_proposals:
            with st.expander(f"🛠️ {patch.file} — {patch.explanation}"):
                st.markdown("**Before**")
                st.code(patch.before, language="python")
                st.markdown("**After**")
                st.code(patch.after, language="python")

    with tabs[3]:
        st.markdown(
            """
**Agentic workflow**

`Code Analyst` + `Security Reviewer` + `Test Engineer`
→ **parallel**
→ `Patch Engineer`
→ `Quality Judge`

The OpenAI Agents SDK traces agent runs, model generations and tool calls,
which lets you inspect the workflow outside this UI.
"""
        )
        st.json(meta)

    payload = report.model_dump_json(indent=2)
    st.download_button(
        "Download JSON report",
        data=payload,
        file_name="repo-review-report.json",
        mime="application/json",
        use_container_width=True,
    )

    if report.quality_notes:
        st.markdown("### Quality notes")
        for note in report.quality_notes:
            st.write(f"• {note}")

    if report.tradeoffs:
        st.markdown("### Engineering trade-offs")
        for tradeoff in report.tradeoffs:
            st.write(f"• {tradeoff}")


def main():
    # Streamlit Cloud exposes secrets through st.secrets rather than the
    # process environment. Copy the API key into the environment before the
    # Agents SDK creates its OpenAI client.
    if not os.getenv("OPENAI_API_KEY"):
        try:
            secret_key = st.secrets.get("OPENAI_API_KEY")
            if secret_key:
                os.environ["OPENAI_API_KEY"] = str(secret_key)
        except Exception:
            pass

    st.set_page_config(
        page_title="RepoReviewer",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .hero {
            padding: 1.2rem 1.4rem;
            border-radius: 18px;
            background: linear-gradient(135deg, #5b4bdb, #7c5cff);
            color: white;
            margin-bottom: 1rem;
        }
        .hero h1 { margin: 0; }
        .hero p { margin: .35rem 0 0; opacity: .9; }
        </style>

        <div class="hero">
          <h1>🤖 RepoReviewer</h1>
          <p>Agentic Python code review, testing and patch assistant.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write(
        "Upload a small Python project, or use the included demo. "
        "The agents inspect the repository, run deterministic static analysis, "
        "propose fixes, and pass the result through a quality gate."
    )

    with st.sidebar:
        st.header("Project")
        use_demo = st.toggle("Use included demo", value=True)
        uploaded = st.file_uploader(
            "Upload project files",
            type=[x.lstrip(".") for x in sorted(ALLOWED_EXTENSIONS)],
            accept_multiple_files=True,
            help="For the fastest demo, upload 3–10 small source files.",
        )

        st.divider()
        st.caption("Safety")
        st.caption(
            "Uploaded code is inspected as text. RepoReviewer does not execute "
            "uploaded Python. Ruff is used only for static analysis."
        )

        run = st.button(
            "🚀 Run agentic review",
            type="primary",
            use_container_width=True,
            disabled=not (use_demo or uploaded),
        )

    if run:
        try:
            if uploaded and not use_demo:
                root = _save_uploads(uploaded)
            else:
                root = _load_demo()

            with st.status("Running agentic workflow...", expanded=True) as status:
                st.write("1/4 — Running Code Analyst, Security Reviewer and Test Engineer in parallel.")
                result = asyncio.run(review_project(root))
                st.write("2/4 — Patch Engineer generated minimal proposals.")
                st.write("3/4 — Quality Judge filtered and scored the findings.")
                st.write("4/4 — Building report.")
                status.update(
                    label="Agentic review complete",
                    state="complete",
                    expanded=False,
                )

            st.session_state["result"] = result
        except Exception as exc:
            st.error(f"Review failed: {exc}")

    if "result" in st.session_state:
        _render_report(st.session_state["result"])
    else:
        st.info("Choose the demo project and click **Run agentic review**.")


if __name__ == "__main__":
    main()
