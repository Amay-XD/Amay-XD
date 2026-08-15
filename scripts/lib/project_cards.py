#!/usr/bin/env python3
# Purpose: turn sort-ready featured-project data into GitHub-safe static cards.
"""Purpose: turn sort-ready featured-project data into GitHub-safe static cards."""

from __future__ import annotations

from .github_api import Repository
from .render import escape_html, format_updated, truncate


def _render_card(repository: Repository) -> str:
    """Render exactly one featured-project card as a safe HTML table row."""
    description = truncate(repository.description or "No description provided.")
    link = (
        f'<a href="{escape_html(repository.url)}">'
        f"<strong>{escape_html(repository.name)}</strong></a>"
    )
    language = escape_html(repository.language or "—")
    updated = format_updated(repository.updated_at)
    meta = f"🗂 {language} &nbsp;·&nbsp; ⭐ {repository.stars} &nbsp;·&nbsp; {updated}"

    return (
        "  <tr>\n"
        "    <td>\n"
        f"      {link}<br />\n"
        f"      {escape_html(description)}<br />\n"
        f"      <sub>{meta}</sub>\n"
        "    </td>\n"
        "  </tr>"
    )


def render_project_cards(repositories: list[Repository]) -> str:
    """Render cards or the honest empty state when no public repositories exist."""
    if not repositories:
        return (
            '<div align="center">\n\n'
            "No public repositories yet — check back soon\n\n"
            "</div>"
        )
    cards = "\n".join(_render_card(repository) for repository in repositories)
    return (
        '<div align="center">\n\n'
        f"<table>\n<tbody>\n{cards}\n</tbody>\n</table>\n\n"
        "</div>"
    )
