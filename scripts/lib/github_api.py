#!/usr/bin/env python3
# Purpose: fetch public GitHub repository data for the profile README.
"""Purpose: fetch public GitHub repository data for the profile README."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://api.github.com"
GRAPHQL_URL = f"{API_URL}/graphql"
MAX_RETRIES = 3

GRAPHQL_QUERY = """
query ProfileRepositories($login: String!, $cursor: String) {
  user(login: $login) {
    pinnedItems(first: 100, types: [REPOSITORY]) {
      nodes {
        ... on Repository {
          name description url stargazerCount updatedAt isFork isPrivate
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
        name description url stargazerCount updatedAt isFork isPrivate
        primaryLanguage { name }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""


class GitHubAPIError(RuntimeError):
    """Raised when GitHub data cannot be retrieved safely."""


@dataclass(frozen=True)
class Repository:
    """The fields needed to render a featured-project card."""

    name: str
    description: str | None
    language: str | None
    stars: int
    updated_at: str
    url: str

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> "Repository":
        """Build a repository from GitHub REST or GraphQL response data."""
        language = value.get("primaryLanguage") or value.get("language")
        if isinstance(language, dict):
            language = language.get("name")
        return cls(
            name=str(value["name"]),
            description=value.get("description"),
            language=language,
            stars=int(value.get("stargazerCount", value.get("stargazers_count", 0))),
            updated_at=str(
                value["updatedAt"] if "updatedAt" in value else value["updated_at"]
            ),
            url=str(value.get("html_url") or value["url"]),
        )


class GitHubClient:
    """Small GitHub API client with pagination and rate-limit retries."""

    def __init__(self, token: str, username: str) -> None:
        self._token = token
        self._username = username

    def _request_json(
        self, url: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Send an authenticated GitHub request and retry short rate limits."""
        body = json.dumps(payload).encode("utf-8") if payload else None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "User-Agent": f"{self._username}-profile-readme-updater",
        }
        if body:
            headers["Content-Type"] = "application/json"

        for attempt in range(MAX_RETRIES):
            request = Request(
                url,
                data=body,
                headers=headers,
                method="POST" if body else "GET",
            )
            try:
                with urlopen(request, timeout=30) as response:
                    return json.load(response)
            except HTTPError as error:
                retry_after = error.headers.get("Retry-After")
                reset_at = error.headers.get("X-RateLimit-Reset")
                if error.code in (403, 429) and attempt + 1 < MAX_RETRIES:
                    wait_seconds = self._retry_wait(retry_after, reset_at)
                    print(f"GitHub rate limit reached; retrying in {wait_seconds}s.")
                    time.sleep(wait_seconds)
                    continue
                raise GitHubAPIError(
                    f"GitHub API request failed: HTTP {error.code}"
                ) from error
            except URLError as error:
                raise GitHubAPIError(
                    f"GitHub API request failed: {error.reason}"
                ) from error
        raise GitHubAPIError("GitHub API retry budget was exhausted.")

    @staticmethod
    def _retry_wait(retry_after: str | None, reset_at: str | None) -> int:
        """Return a bounded delay from GitHub's retry or reset headers."""
        if retry_after and retry_after.isdigit():
            return min(max(int(retry_after), 1), 60)
        if reset_at and reset_at.isdigit():
            return min(max(int(reset_at) - int(time.time()), 1), 60)
        return 5

    def fetch_graphql(self) -> tuple[list[Repository], list[Repository]]:
        """Fetch pinned repositories and all public owned repositories via GraphQL."""
        cursor: str | None = None
        pinned: list[Repository] = []
        repositories: list[Repository] = []
        while True:
            response = self._request_json(
                GRAPHQL_URL,
                {
                    "query": GRAPHQL_QUERY,
                    "variables": {"login": self._username, "cursor": cursor},
                },
            )
            if not isinstance(response, dict) or response.get("errors"):
                raise GitHubAPIError(f"GitHub GraphQL returned errors: {response}")
            user = response.get("data", {}).get("user")
            if not user:
                raise GitHubAPIError(f"GitHub user {self._username!r} was not found.")
            if cursor is None:
                pinned = self._repositories_from_nodes(user["pinnedItems"]["nodes"])
            connection = user["repositories"]
            repositories.extend(self._repositories_from_nodes(connection["nodes"]))
            page_info = connection["pageInfo"]
            if not page_info["hasNextPage"]:
                return pinned, repositories
            cursor = page_info["endCursor"]

    def fetch_rest(self) -> list[Repository]:
        """Fetch all public owned repositories through the REST fallback endpoint."""
        repositories: list[Repository] = []
        page = 1
        while True:
            query = urlencode(
                {
                    "type": "owner",
                    "sort": "updated",
                    "direction": "desc",
                    "per_page": 100,
                    "page": page,
                }
            )
            response = self._request_json(
                f"{API_URL}/users/{self._username}/repos?{query}"
            )
            if not isinstance(response, list):
                raise GitHubAPIError(
                    f"GitHub REST returned an unexpected response: {response}"
                )
            repositories.extend(self._repositories_from_nodes(response))
            if len(response) < 100:
                return repositories
            page += 1

    @staticmethod
    def _repositories_from_nodes(
        nodes: list[dict[str, Any] | None],
    ) -> list[Repository]:
        """Exclude private and forked nodes, then convert them to repositories."""
        return [
            Repository.from_api(node)
            for node in nodes
            if node and not node.get("isPrivate", node.get("private", False))
            and not node.get("isFork", node.get("fork", False))
        ]


def get_public_repositories(token: str, username: str) -> list[Repository]:
    """Return pinned repositories first, then all remaining repositories by rank."""
    client = GitHubClient(token, username)
    try:
        pinned, repositories = client.fetch_graphql()
        print("Featured projects source: GitHub GraphQL API.")
    except GitHubAPIError as error:
        print(f"GitHub GraphQL failed ({error}); using REST fallback.")
        pinned = []
        repositories = client.fetch_rest()
        print("Featured projects source: GitHub REST API fallback.")

    pinned_names = {repository.name for repository in pinned}
    remaining = [
        repository
        for repository in repositories
        if repository.name not in pinned_names
    ]
    remaining.sort(
        key=lambda repository: (repository.stars, repository.updated_at),
        reverse=True,
    )
    return pinned + remaining
