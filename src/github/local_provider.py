"""
Local Repository Provider for reading repository data from local file system.
"""
import os
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

from typing import Optional, List, Set

import aiohttp
import aiofiles

from src.github.fetch_repo import RepoDetails, RepoTreeResult

# UTC+8 timezone (e.g., China Standard Time)
UTC8 = timezone(timedelta(hours=8))

# Directories and files to ignore when scanning local repositories
DEFAULT_IGNORE_PATTERNS: Set[str] = {
    # Version control
    '.git',
    '.svn',
    '.hg',
    
    # IDE / Editor
    '.idea',
    '.vscode',
    '.vs',
    '*.swp',
    '*.swo',
    
    # Python
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.tox',
    '*.pyc',
    '*.pyo',
    '.eggs',
    '*.egg-info',
    '.venv',
    'venv',
    'env',
    
    # Node.js
    'node_modules',
    
    # Build artifacts
    'build',
    'dist',
    'target',
    '.gradle',
    
    # OS files
    '.DS_Store',
    'Thumbs.db',
    
    # Logs and temp
    '*.log',
    'tmp',
    'temp',
    '.cache',
}


class LocalRepoProvider:
    """Repository provider that reads data from the local file system."""

    def __init__(
        self,
        base_path: str,
        ignore_patterns: Optional[Set[str]] = None,
        source_url: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ):
        """
        Initialize the local repository provider.

        Args:
            base_path: The root directory of the local repository.
            ignore_patterns: Optional set of patterns to ignore (defaults to DEFAULT_IGNORE_PATTERNS).
            source_url: Optional URL to use in RepoDetails (for consistency with view layer).
            owner: Optional owner name to use in RepoDetails.
            repo: Optional repo name to use in RepoDetails.
        """
        self.base_path = Path(base_path).resolve()
        self.ignore_patterns = ignore_patterns if ignore_patterns is not None else DEFAULT_IGNORE_PATTERNS
        # Store provided identifiers for consistent responses
        self._source_url = source_url
        self._owner = owner
        self._repo = repo

        if not self.base_path.exists():
            raise ValueError(f"Local repository path does not exist: {self.base_path}")
        if not self.base_path.is_dir():
            raise ValueError(f"Local repository path is not a directory: {self.base_path}")
    
    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored based on ignore patterns."""
        name = path.name
        
        # Check exact match
        if name in self.ignore_patterns:
            return True
        
        # Check glob patterns (simple implementation)
        for pattern in self.ignore_patterns:
            if pattern.startswith('*') and name.endswith(pattern[1:]):
                return True
        
        return False
    
    def _generate_sha(self) -> str:
        """Generate a unique SHA for the local repository snapshot."""
        # Use timestamp + path hash for a unique identifier
        timestamp = datetime.now().isoformat()
        path_hash = hashlib.sha1(str(self.base_path).encode()).hexdigest()[:8]
        return f"local-{path_hash}-{timestamp.replace(':', '-').replace('.', '-')}"
    
    async def get_details(self, owner: str, repo: str) -> RepoDetails:
        """
        Get repository details for a local repository.

        Uses provided identifiers from __init__ if available, otherwise auto-generates.
        This ensures consistency with the Repository record created by the view layer.
        """
        # Use provided identifiers if available, otherwise auto-generate
        repo_name = self._repo if self._repo else self.base_path.name
        repo_owner = self._owner if self._owner else "local"
        url = self._source_url if self._source_url else f"local://{self.base_path}"
        sha = self._generate_sha()

        return RepoDetails(
            repo_owner=repo_owner,
            repo_name=repo_name,
            url=url,
            topics=[],
            language=self._detect_language(),
            description=f"Local repository: {self.base_path}",
            stars=0,
            forks=0,
            default_branch="local",
            sha=sha,
            commit_at=datetime.now(UTC8)
        )
    
    def _detect_language(self) -> Optional[str]:
        """Attempt to detect the primary language of the repository."""
        # Simple heuristic: check for common project files
        indicators = {
            'Python': ['setup.py', 'pyproject.toml', 'requirements.txt', 'Pipfile'],
            'JavaScript': ['package.json'],
            'TypeScript': ['tsconfig.json'],
            'Java': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
            'Go': ['go.mod'],
            'Rust': ['Cargo.toml'],
            'Ruby': ['Gemfile'],
            'PHP': ['composer.json'],
            'C#': ['*.csproj', '*.sln'],
        }
        
        for lang, files in indicators.items():
            for file_pattern in files:
                if file_pattern.startswith('*'):
                    # Glob pattern
                    if list(self.base_path.glob(file_pattern)):
                        return lang
                else:
                    if (self.base_path / file_pattern).exists():
                        return lang
        
        return None
    
    async def get_tree(self, owner: str, repo: str, commit_sha: str) -> RepoTreeResult:
        """
        Build the file tree for a local repository.
        
        owner, repo, and commit_sha are ignored for local repos.
        """
        return self._build_tree(self.base_path, "")
    
    def _build_tree(self, current_path: Path, relative_path: str) -> RepoTreeResult:
        """Recursively build the file tree structure."""
        files: List[str] = []
        subdirectories: List[RepoTreeResult] = []
        
        try:
            for item in sorted(current_path.iterdir()):
                if self._should_ignore(item):
                    continue
                
                item_relative_path = f"{relative_path}/{item.name}" if relative_path else item.name
                
                if item.is_file():
                    files.append(item_relative_path)
                elif item.is_dir():
                    subdir_tree = self._build_tree(item, item_relative_path)
                    # Only include non-empty directories
                    if subdir_tree.files or subdir_tree.subdirectories:
                        subdirectories.append(subdir_tree)
        except PermissionError:
            # Skip directories we can't access
            pass
        
        return RepoTreeResult(
            path=relative_path,
            files=files,
            subdirectories=subdirectories
        )
    
    async def get_file_content(
        self, owner: str, repo: str, sha: str, path: str,
        session: Optional[aiohttp.ClientSession] = None
    ) -> str:
        """
        Read file content from the local file system.
        
        owner, repo, sha, and session are ignored for local repos.
        """
        file_path = self.base_path / path
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        except UnicodeDecodeError:
            # Try with latin-1 for binary-ish files
            async with aiofiles.open(file_path, 'r', encoding='latin-1') as f:
                return await f.read()
