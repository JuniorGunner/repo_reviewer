import subprocess
from pathlib import Path

from agents import RunContextWrapper, function_tool

from app.config import ALLOWED_EXTENSIONS, MAX_CHARS_PER_FILE
from app.context import ReviewContext


def _safe_path(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    root = root.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Path escapes the uploaded project.")
    if not candidate.is_file():
        raise FileNotFoundError(f"File not found: {relative_path}")
    if candidate.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {candidate.suffix}")
    return candidate


@function_tool
def list_project_files(ctx: RunContextWrapper[ReviewContext]) -> str:
    """List the files available in the uploaded project."""
    root = ctx.context.root
    files = [
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
    ]
    return "\n".join(sorted(files)) or "No supported source files found."


@function_tool
def read_project_file(
    ctx: RunContextWrapper[ReviewContext],
    path: str,
) -> str:
    """Read one source file from the uploaded project.

    Args:
        path: Relative path returned by list_project_files.
    """
    file_path = _safe_path(ctx.context.root, path)
    data = file_path.read_text(encoding="utf-8", errors="replace")
    if len(data) > MAX_CHARS_PER_FILE:
        data = data[:MAX_CHARS_PER_FILE] + "\n...[truncated]..."
    return data


@function_tool
def run_ruff(ctx: RunContextWrapper[ReviewContext]) -> str:
    """Run Ruff static analysis on the uploaded project without executing its code."""
    root = ctx.context.root
    try:
        result = subprocess.run(
            ["ruff", "check", "."],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except FileNotFoundError:
        return "Ruff is not installed in this environment."
    except subprocess.TimeoutExpired:
        return "Ruff timed out after 20 seconds."

    output = (result.stdout + "\n" + result.stderr).strip()
    if not output:
        output = "Ruff completed with no findings."
    return f"exit_code={result.returncode}\n{output[:12000]}"
