"""
Repository Provider abstraction for fetching repository data from different sources.
"""
import os
from abc import ABC, abstractmethod
from typing import Optional, Protocol
from dataclasses import dataclass

import aiohttp

from github.fetch_repo import (
    RepoDetails, RepoTreeResult,
    fetch_github_repo_details, fetch_github_repo_tree, fetch_github_repo_file
)


class RepoProvider(Protocol):
    """Protocol defining the interface for repository data providers."""
    
    async def get_details(self, owner: str, repo: str) -> RepoDetails:
        """Fetch repository metadata."""
        ...
    
    async def get_tree(self, owner: str, repo: str, commit_sha: str) -> RepoTreeResult:
        """Fetch the full file tree of the repository."""
        ...
    
    async def get_file_content(
        self, owner: str, repo: str, sha: str, path: str,
        session: Optional[aiohttp.ClientSession] = None
    ) -> str:
        """Fetch the content of a single file."""
        ...


class GitHubRepoProvider:
    """Repository provider that fetches data from GitHub API."""
    
    async def get_details(self, owner: str, repo: str) -> RepoDetails:
        """Fetch repository details from GitHub."""
        return await fetch_github_repo_details(owner, repo)
    
    async def get_tree(self, owner: str, repo: str, commit_sha: str) -> RepoTreeResult:
        """Fetch the repository file tree from GitHub."""
        return await fetch_github_repo_tree(owner, repo, commit_sha)
    
    async def get_file_content(
        self, owner: str, repo: str, sha: str, path: str,
        session: Optional[aiohttp.ClientSession] = None
    ) -> str:
        """Fetch file content from GitHub."""
        return await fetch_github_repo_file(owner, repo, sha, path, session)


def get_repo_provider() -> RepoProvider:
    """
    Factory function to get the appropriate repository provider based on environment config.
    
    Returns GitHubRepoProvider by default, or LocalRepoProvider if REPO_SOURCE_TYPE=local.
    """
    source_type = os.getenv("REPO_SOURCE_TYPE", "github").lower()
    
    if source_type == "local":
        from github.local_provider import LocalRepoProvider
        local_path = os.getenv("LOCAL_REPO_PATH")
        if not local_path:
            raise ValueError("LOCAL_REPO_PATH environment variable is required when REPO_SOURCE_TYPE=local")
        return LocalRepoProvider(base_path=local_path)
    
    return GitHubRepoProvider()
