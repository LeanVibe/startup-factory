#!/usr/bin/env python
"""
meta_fill.py  –  Scan a folder of Markdown / YAML docs, detect gaps in the
                 minimum‑required set, and fill them using Gemini‑CLI with
                 web search.  Prompts for up to five critical pieces of data
                 it cannot infer.  If deep desk‑research is still required,
                 it writes a self‑contained prompt to `perplexity‑research.md`.

Prereqs:
  - Python ≥3.10
  - `gemini` CLI in PATH, authenticated (`gcloud auth application-default login`
    or equivalent)
  - `pyyaml`, `rich` (for nice console output)

Usage:
    python meta_fill.py /path/to/project/docs
"""

import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple

import yaml
from rich.prompt import Prompt

DOC_SCHEMA: Dict[str, List[str]] = {
    "mvp-spec.md": [
        "## Problem statement",
        "## User stories",
        "## Non‑functional constraints",
    ],
    "architecture.md": [
        "## Context diagram",
        "## Component diagram",
        "## Key decisions",
    ],
    "api.yaml": ["openapi: 3.1.0"],
    "test-plan.md": ["## Critical paths", "## Performance budgets"],
    "prompt-library.md": ["## Prompt patterns"],
}

MAX_QUESTIONS = 5
QUESTION_COUNT = 0


def run_gemini(prompt: str) -> str:
    """Call Gemini CLI with web search enabled and return markdown output."""
    cmd = ["gemini", "--web", "--output", "markdown", "-p", prompt]
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def file_missing_or_incomplete(fp: Path, must_have: List[str]) -> bool:
    if not fp.exists():
        return True
    content = fp.read_text(encoding="utf‑8")
    return not all(marker.lower() in content.lower() for marker in must_have)


def smart_question(question: str) -> str:
    global QUESTION_COUNT
    if QUESTION_COUNT >= MAX_QUESTIONS:
        return "UNKNOWN"
    answer = Prompt.ask(f"[bold cyan]{question}[/]")
    QUESTION_COUNT += 1
    return answer


def build_gemini_prompt(
    filename: str, markers: List[str], answers: Dict[str, str]
) -> str:
    need = ", ".join(m.strip("# ").strip() for m in markers)
    extra_info = "\n".join(f"{k}: {v}" for k, v in answers.items() if v != "UNKNOWN")
    return textwrap.dedent(
        f"""
        You are an expert startup CTO.  Create **{filename}** containing the following
        missing sections so that Claude‑Code can start development immediately.

        Required sections still missing: {need}

        Project context (from founder answers or existing docs):
        {extra_info or "(no extra context)"}

        ⋯ Please respond with the complete file content only, in markdown (or yaml for api.yaml).
        """
    ).strip()


def main(docs_dir: Path) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    answers: Dict[str, str] = {}
    research_needed: List[str] = []

    # Scan each required doc
    for fname, markers in DOC_SCHEMA.items():
        fp = docs_dir / fname

        if file_missing_or_incomplete(fp, markers):
            # Ask up to five questions for critical info the model probably can't guess
            if "mvp-spec" in fname and "Problem statement" in markers[0]:
                answers["Problem statement"] = smart_question(
                    "What ONE‑SENTENCE problem does this MVP solve?"
                )
            elif "api.yaml" == fname:
                answers["Main resource name (e.g. 'Task', 'Note')"] = smart_question(
                    "What is the primary resource for the API?"
                )

            # Generate file content with Gemini
            gemini_prompt = build_gemini_prompt(fname, markers, answers)
            print(f"→ Calling Gemini to write {fname} …")
            content = run_gemini(gemini_prompt)
            fp.write_text(content, encoding="utf‑8")
        else:
            print(f"✓ {fname} already complete")

    # Detect if deeper market‑size or competitor research still missing
    spec_path = docs_dir / "mvp-spec.md"
    if spec_path.exists():
        spec = spec_path.read_text(encoding="utf‑8")
        if not re.search(r"##\s*Market.*size", spec, re.I):
            research_needed.append("Market size & growth rate")
        if "## Competitive analysis" not in spec:
            research_needed.append("Competitive landscape")

    if research_needed:
        prompt_lines = [
            "You are Perplexity AI.  Perform desk research and summarise the following:",
            *[f"• {item}" for item in research_needed],
            "",
            "Present the answer in markdown with citations.",
        ]
        (docs_dir / "perplexity-research.md").write_text(
            "\n".join(prompt_lines), encoding="utf‑8"
        )
        print(
            "⚠️  Created **perplexity-research.md** – run this in Perplexity when ready."
        )

    print("\n✅ All required docs now exist or have prompts ready.")
    if QUESTION_COUNT >= MAX_QUESTIONS:
        print(
            "ℹ️  Maximum question limit reached; review placeholders marked 'UNKNOWN'."
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: meta_fill.py <docs‑folder>")
    main(Path(sys.argv[1]))
