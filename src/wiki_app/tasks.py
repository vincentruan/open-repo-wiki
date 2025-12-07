from celery import shared_task
from asgiref.sync import async_to_sync
from loguru import logger
from typing import Optional

from .services import InsertRepoService
from .utils import is_celery_available
from llm.llm_factory import LLMFactory
from llm.llm_config import LLMConfig


def _execute_repository_processing(
    owner: str, 
    repo: str, 
    source_type: str = 'github',
    source_path: Optional[str] = None
):
    """
    Execute repository processing synchronously.
    This is used both by the Celery task and the sync fallback.
    
    Args:
        owner: Repository owner
        repo: Repository name
        source_type: 'github', 'local', or 'git'
        source_path: For 'local', the file path; for 'git', the clone URL
    """
    llm_config = LLMConfig(1, 0.95, 0, 8192)
    
    # Create appropriate provider based on source type
    if source_type == 'local':
        from github.local_provider import LocalRepoProvider
        provider = LocalRepoProvider(source_path)
    elif source_type == 'git':
        from github.git_provider import GitRepoProvider
        provider = GitRepoProvider(source_path)
    else:
        # Default to GitHub
        from github.provider import GitHubRepoProvider
        provider = GitHubRepoProvider()
    
    service = InsertRepoService(
        llm_provider=LLMFactory.create_provider(llm_config=llm_config),
        repo_provider=provider
    )
    async_to_sync(service.insertRepository)(owner, repo)


@shared_task
def process_repository_task(
    owner: str, 
    repo: str,
    source_type: str = 'github',
    source_path: Optional[str] = None
):
    """
    Celery task for processing a repository asynchronously.
    """
    _execute_repository_processing(owner, repo, source_type, source_path)


def run_repository_task(
    owner: str, 
    repo: str,
    source_type: str = 'github',
    source_path: Optional[str] = None
) -> dict:
    """
    Run repository processing task.
    
    If Celery/Redis is available, queues the task for async processing.
    Otherwise, runs the task synchronously (blocking).
    
    Args:
        owner: Repository owner
        repo: Repository name
        source_type: 'github', 'local', or 'git'
        source_path: For 'local', the file path; for 'git', the clone URL
    
    Returns:
        dict with 'mode' ('async' or 'sync') and 'task_id' (if async)
    """
    if is_celery_available():
        logger.info(f"Queuing repository {owner}/{repo} ({source_type}) for async processing")
        result = process_repository_task.delay(owner, repo, source_type, source_path)
        return {'mode': 'async', 'task_id': str(result.id)}
    else:
        logger.info(f"Processing repository {owner}/{repo} ({source_type}) synchronously")
        _execute_repository_processing(owner, repo, source_type, source_path)
        return {'mode': 'sync', 'task_id': None}


