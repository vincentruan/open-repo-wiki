"""
Utility functions for wiki_app.
"""
import os
import re
from typing import Tuple, Dict, Optional
from loguru import logger


def celery_available() -> bool:
    """
    Check if Celery broker (Redis) is available.
    
    Returns True if Celery is configured and the broker is reachable,
    False otherwise (for local development without Redis).
    """
    broker_url = os.getenv('CELERY_BROKER_URL', '')
    
    # If no broker URL configured, Celery is not available
    if not broker_url:
        logger.info("No CELERY_BROKER_URL configured, running in sync mode")
        return False
    
    try:
        import redis
        # Parse Redis URL and try to connect
        # Expected format: redis://host:port/db
        if broker_url.startswith('redis://'):
            parts = broker_url.replace('redis://', '').split('/')
            host_port = parts[0].split(':')
            host = host_port[0] if host_port[0] else 'localhost'
            port = int(host_port[1]) if len(host_port) > 1 else 6379
            
            client = redis.Redis(host=host, port=port, socket_timeout=1)
            client.ping()
            return True
    except ImportError:
        logger.warning("Redis package not installed, running in sync mode")
        return False
    except Exception as e:
        logger.info(f"Redis not available ({e}), running in sync mode")
        return False
    
    return False


# Cache the result to avoid repeated connection checks
_celery_available_cache = None


def is_celery_available() -> bool:
    """
    Cached version of celery_available().
    Checks once per process lifecycle.
    """
    global _celery_available_cache
    if _celery_available_cache is None:
        _celery_available_cache = celery_available()
    return _celery_available_cache


def parse_github_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a GitHub URL or owner/repo string and extract owner and repo.
    
    Supports:
    - https://github.com/owner/repo
    - github.com/owner/repo
    - owner/repo
    
    Returns (owner, repo) tuple, or (None, None) if parsing fails.
    """
    url = url.strip().rstrip('/')
    if url.endswith('.git'):
        url = url[:-4]
    
    # Extract path after github.com
    if 'github.com/' in url:
        path = url.split('github.com/')[-1]
    else:
        path = url
    
    parts = [p for p in path.split('/') if p]
    
    if len(parts) >= 2:
        return parts[0], parts[1]
    
    return None, None


def detect_source_type(query: str, explicit_type: Optional[str] = None) -> Tuple[str, Dict]:
    """
    Detect the source type from user input.
    
    Args:
        query: The user input (URL, path, or owner/repo)
        explicit_type: Explicitly specified source type from UI (github, local, git)
    
    Returns:
        Tuple of (source_type, parsed_info)
        - source_type: 'github', 'local', 'git', or 'unknown'
        - parsed_info: Dict with relevant parsed data
    """
    query = query.strip()
    
    # If explicit type is provided and valid, use it
    if explicit_type in ('github', 'local', 'git'):
        if explicit_type == 'github':
            owner, repo = parse_github_url(query)
            if owner and repo:
                return 'github', {'owner': owner, 'repo': repo}
            return 'unknown', {'error': 'Invalid GitHub repository format'}
        
        elif explicit_type == 'local':
            # Validate it looks like an absolute path
            if query.startswith('/') or query.startswith('~') or re.match(r'^[A-Z]:\\', query):
                # Expand ~ to home directory
                if query.startswith('~'):
                    query = os.path.expanduser(query)
                return 'local', {'path': query}
            return 'unknown', {'error': 'Please enter an absolute path'}
        
        elif explicit_type == 'git':
            # Accept any URL-like input for git
            if query.startswith('http') or query.startswith('git@') or '.git' in query:
                return 'git', {'url': query}
            # Try to construct a URL
            return 'git', {'url': query}
    
    # Auto-detect based on input pattern
    
    # Check for local path patterns
    if query.startswith('/') or query.startswith('~') or re.match(r'^[A-Z]:\\', query):
        if query.startswith('~'):
            query = os.path.expanduser(query)
        return 'local', {'path': query}
    
    # Check for GitHub patterns
    if 'github.com' in query:
        owner, repo = parse_github_url(query)
        if owner and repo:
            return 'github', {'owner': owner, 'repo': repo}
    
    # Check for other Git hosts
    git_hosts = ['gitlab.com', 'bitbucket.org', 'gitee.com', 'codeberg.org']
    if any(host in query for host in git_hosts):
        return 'git', {'url': query}
    
    # Check for generic git URL patterns
    if query.startswith('git@') or (query.startswith('http') and '.git' in query):
        return 'git', {'url': query}
    
    # Default: assume owner/repo format for GitHub
    if '/' in query and not query.startswith('http'):
        parts = [p for p in query.split('/') if p]
        if len(parts) >= 2 and re.match(r'^[a-zA-Z0-9_-]+$', parts[0]):
            return 'github', {'owner': parts[0], 'repo': parts[1]}
    
    return 'unknown', {'error': 'Could not determine source type'}

