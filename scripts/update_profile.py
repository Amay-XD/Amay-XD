#!/usr/bin/env python3
"""Refresh the Featured Projects section in the GitHub profile README."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USERNAME = "Amay-XD"
ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
API_URL = "https://api.github.com/graphql"
START_MARKER = "## Featured Projects"
END_MARKER = "## Certifications"

QUERY = """
query ProfileRepositories($login: String!, $cursor: String) {
  user(login: $login) {
    pinnedItems(first: 6, types: [REPOSITORY]) {
      nodes {
        ... on Repository {
          name
          description
          url
          stargazerCount
          updatedAt
          isPrivate
          primaryLanguage { name }
        }
      }
    }
    repositories(
      first: 100
      after: $cursor
      privacy: PUBLIC
      ownerAffiliations: OWNER
      orderBy: {field: UPDATED_AT, direction: DESC}
    ) {
      nodes {
        name
        description
        url
        stargazerCount
        updatedAt
        primaryLanguage { name }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""


def request_repositories(token: str, cursor: str | None = None) -> dict[str, Any]:
    """Fetch one page of public repositories and the user's pinned items."""
    payload = json.dumps(
        {"query": QUERY, "variables": {"login": USERNAME, "cursor": cursor}}
    ).encode("utf-8")
    request = Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{USERNAME}-profile-readme-updater",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            data: dict[str, Any] = json.load(response)
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"GitHub API request failed: {error}") from error

    if data.get("errors"):
        raise RuntimeError(f"GitHub GraphQL returned errors: {data['errors']}")
    return data


def get_repositories(token: str) -> list[dict[str, Any]]:
    """Return pinned public repositories first, then all remaining public repos."""
    cursor: str | None = None
    repositories: list[dict[str, Any]] = []
    pinned: list[dict[str, Any]] = []

    while True:
        user = request_repositories(token, cursor)["data"]["user"]
        if user is None:
            raise RuntimeError(f"GitHub user {USERNAME!r} was not found.")

        if cursor is None:
            pinned = [
                repo
                for repo in user["pinnedItems"]["nodes"]
                if repo is not None and not repo.get("isPrivate", False)
            ]

        connection = user["repositories"]
        repositories.extend(connection["nodes"])
        page_info = connection["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

    pinned_names = {repo["name"] for repo in pinned}
    remaining = [repo for repo in repositories if repo["name"] not in pinned_names]
    remaining.sort(
        key=lambda repo: (repo["stargazerCount"], repo["updatedAt"]), reverse=True
    )
    return pinned + remaining


def clean_text(value: str | None, fallback: str) -> str:
    """Prepare API text for safe use inside a Markdown table cell."""
    if not value:
        return fallback
    return " ".join(value.split()).replace("|", "\\|")


def updated_date(timestamp: str) -> str:
    """Format GitHub's ISO timestamp as a compact, locale-independent date."""
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime(
        "%d %b %Y"
    )


def project_cell(repository: dict[str, Any]) -> str:
    """Render one compact, GitHub-safe project card cell."""
    name = clean_text(repository["name"], "Untitled repository")
    description = clean_text(repository.get("description"), "No description provided.")
    language = clean_text(
        (repository.get("primaryLanguage") or {}).get("name"), "Not specified"
    )
    stars = repository["stargazerCount"]
    date = updated_date(repository["updatedAt"])
    url = repository["url"]
    return (
        f"[**{name}**]({url})<br>"
        f"{description}<br>"
        f"<sub>⌘ {language} &nbsp; ★ {stars} &nbsp; Updated {date}</sub>"
    )


def render_projects(repositories: list[dict[str, Any]]) -> str:
    """Render a responsive two-column table without unsupported README styling."""
    if not repositories:
        return (
            "> No public repositories yet. New public repositories will appear "
            "automatically after the next update.\n"
        )

    cards = [project_cell(repository) for repository in repositories]
    rows = ["| Project | Project |", "| :--- | :--- |"]
    for index in range(0, len(cards), 2):
        right = cards[index + 1] if index + 1 < len(cards) else ""
        rows.append(f"| {cards[index]} | {right} |")
    return "\n".join(rows) + "\n"


def replace_projects(readme: str, projects: str) -> str:
    """Replace only the generated area between stable README section headings."""
    start = readme.find(START_MARKER)
    end = readme.find(END_MARKER)
    if start == -1 or end == -1 or start >= end:
        raise RuntimeError("README project section markers are missing or out of order.")

    section_start = start + len(START_MARKER)
    return f"{readme[:section_start]}\n\n{projects}\n{readme[end:]}"


def main() -> int:
    """Update README.md, returning a non-zero status for unsafe API failures."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required to refresh the profile README.", file=sys.stderr)
        return 1

    try:
        repositories = get_repositories(token)
        updated_readme = replace_projects(
            README_PATH.read_text(encoding="utf-8"), render_projects(repositories)
        )
        README_PATH.write_text(updated_readme, encoding="utf-8")
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"Profile update failed: {error}", file=sys.stderr)
        return 1

    print(f"Rendered {len(repositories)} public repositories into README.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
