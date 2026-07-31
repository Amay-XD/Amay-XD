#!/usr/bin/env python3
# Purpose: generate README.md from the static template and live GitHub projects.
"""Purpose: generate README.md from the static template and live GitHub projects."""

from __future__ import annotations

import os
from pathlib import Path
import sys

from lib.github_api import GitHubAPIError, get_public_repositories
from lib.project_cards import render_project_cards


USERNAME = "Amay-XD"
ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "README.template.md"
README_PATH = ROOT / "README.md"
PROJECTS_TOKEN = "{{FEATURED_PROJECTS}}"
README_HEADER = (
    "<!-- Purpose: generated GitHub profile README. Edit README.template.md, "
    "then run scripts/generate_readme.py. -->\n\n"
)


def generate_readme(token: str) -> str:
    """Inject live project cards into the README template."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if template.count(PROJECTS_TOKEN) != 1:
        raise RuntimeError(
            "README template must contain exactly one featured-project token."
        )
    repositories = get_public_repositories(token, USERNAME)
    content = template.replace(PROJECTS_TOKEN, render_project_cards(repositories))
    return f"{README_HEADER}{content}"


def main() -> int:
    """Write the generated README or fail without changing project data."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required to generate README.md.", file=sys.stderr)
        return 1
    try:
        README_PATH.write_text(generate_readme(token), encoding="utf-8")
    except (GitHubAPIError, OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"README generation failed: {error}", file=sys.stderr)
        return 1
    print("README.md was generated from live GitHub project data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
