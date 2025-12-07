"""
Git Repository Provider - clones any Git URL and provides local file access.
"""
import os
import shutil
import subprocess
import tempfile
import hashlib
from datetime import datetime
from typing import List, Optional
from loguru import logger

from .fetch_repo import RepoDetails, RepoTree, RepoTreeResult


class GitRepoProvider:
    """
    Provider that clones a Git repository to a temp directory and provides
    local file access. Used for non-GitHub Git repositories (GitLab, Bitbucket, etc.).
    """
    
    def __init__(self, git_url: str):
        """
        Initialize the Git provider.
        
        Args:
            git_url: The Git URL to clone (https or git@ format)
        """
        self.git_url = git_url
        self.temp_dir: Optional[str] = None
        self._cloned = False
        self._details: Optional[RepoDetails] = None
    
    def _ensure_cloned(self):
        """Clone the repository if not already done."""
        if self._cloned:
            return
        
        # Create temp directory
        url_hash = hashlib.md5(self.git_url.encode()).hexdigest()[:8]
        self.temp_dir = tempfile.mkdtemp(prefix=f'openrepowiki_{url_hash}_')
        
        logger.info(f"Cloning {self.git_url} to {self.temp_dir}")
        
        try:
            # Clone with depth 1 for speed
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', self.git_url, self.temp_dir],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Git clone failed: {result.stderr}")
                raise Exception(f"Failed to clone repository: {result.stderr}")
            
            self._cloned = True
            logger.info(f"Successfully cloned {self.git_url}")
            
        except subprocess.TimeoutExpired:
            self.cleanup()
            raise Exception("Git clone timed out (5 minutes)")
        except FileNotFoundError:
            self.cleanup()
            raise Exception("Git is not installed or not in PATH")
    
    def cleanup(self):
        """Remove the temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            logger.info(f"Cleaning up temp directory: {self.temp_dir}")
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None
            self._cloned = False
    
    async def get_details(self, owner: str, repo: str) -> RepoDetails:
        """Get repository details after cloning."""
        self._ensure_cloned()
        
        if self._details:
            return self._details
        
        # Get commit SHA from cloned repo
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.temp_dir,
                capture_output=True,
                text=True
            )
            sha = result.stdout.strip() if result.returncode == 0 else f"git-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        except Exception:
            sha = f"git-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Detect primary language (simple heuristic)
        language = self._detect_language()
        
        self._details = RepoDetails(
            owner=owner,
            repo=repo,
            sha=sha,
            language=language
        )
        
        return self._details
    
    def _detect_language(self) -> str:
        """Detect primary language based on file extensions."""
        if not self.temp_dir:
            return "Unknown"
        
        ext_counts = {}
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.cs': 'C#',
            '.cpp': 'C++',
            '.c': 'C',
        }
        
        for root, dirs, files in os.walk(self.temp_dir):
            # Skip .git directory
            dirs[:] = [d for d in dirs if d != '.git']
            
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in language_map:
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
        
        if ext_counts:
            top_ext = max(ext_counts, key=ext_counts.get)
            return language_map.get(top_ext, "Unknown")
        
        return "Unknown"
    
    async def get_tree(self, owner: str, repo: str, sha: str) -> RepoTreeResult:
        """Get file tree from cloned repository."""
        self._ensure_cloned()
        
        tree_items: List[RepoTree] = []
        
        for root, dirs, files in os.walk(self.temp_dir):
            # Skip .git and other ignored directories
            dirs[:] = [d for d in dirs if not self._should_ignore(d)]
            
            for d in dirs:
                dir_path = os.path.join(root, d)
                rel_path = os.path.relpath(dir_path, self.temp_dir)
                tree_items.append(RepoTree(
                    path=rel_path,
                    mode='040000',
                    type='tree',
                    sha=None,
                    size=None,
                    url=None
                ))
            
            for f in files:
                if self._should_ignore(f):
                    continue
                
                file_path = os.path.join(root, f)
                rel_path = os.path.relpath(file_path, self.temp_dir)
                
                try:
                    size = os.path.getsize(file_path)
                except OSError:
                    size = 0
                
                tree_items.append(RepoTree(
                    path=rel_path,
                    mode='100644',
                    type='blob',
                    sha=None,
                    size=size,
                    url=None
                ))
        
        return RepoTreeResult(
            sha=sha,
            url=self.git_url,
            tree=tree_items,
            truncated=False
        )
    
    def _should_ignore(self, name: str) -> bool:
        """Check if a file/directory should be ignored."""
        ignore_dirs = {
            '.git', 'node_modules', '__pycache__', '.venv', 'venv',
            '.idea', '.vscode', 'dist', 'build', '.next', '.nuxt',
            'target', 'vendor', '.gradle', '.mvn', 'coverage',
            '.pytest_cache', '.mypy_cache', '.tox', 'htmlcov'
        }
        
        ignore_extensions = {
            '.pyc', '.pyo', '.class', '.o', '.so', '.dll', '.exe',
            '.log', '.lock', '.tmp', '.temp', '.cache',
            '.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.mp3', '.mp4', '.avi', '.mov', '.wav',
            '.woff', '.woff2', '.ttf', '.eot'
        }
        
        if name in ignore_dirs:
            return True
        
        if name.startswith('.') and name not in {'.gitignore', '.env.example'}:
            return True
        
        ext = os.path.splitext(name)[1].lower()
        if ext in ignore_extensions:
            return True
        
        return False
    
    async def get_file_content(self, owner: str, repo: str, path: str) -> str:
        """Read file content from cloned repository."""
        self._ensure_cloned()
        
        file_path = os.path.join(self.temp_dir, path)
        
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return ""
        
        if not os.path.isfile(file_path):
            logger.warning(f"Not a file: {file_path}")
            return ""
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return ""
    
    def __del__(self):
        """Cleanup on deletion."""
        self.cleanup()
