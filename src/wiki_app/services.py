import asyncio
import aiohttp
import time
from typing import Optional, List, Dict, Set
from asgiref.sync import sync_to_async
from django.db import transaction

from src.agent.index import CodeProcessor, FolderProcessor
from src.agent.dependency_parser import DependencyParser
from src.wiki_app.models import Repository, Branch, Folder, File, Topic
from src.github.fetch_repo import RepoTreeResult
from src.github.provider import RepoProvider, get_repo_provider
from src.github.filterfile import whitelisted_file, blacklisted_file, whitelisted_filter, blacklisted_files, \
    blacklisted_folder, blacklisted_filter
from src.llm.llm_provider import LLMProvider
from src.wiki_app.config import TokenProcessingConfig
from src.wiki_app.allowed_languages import ALLOWED_LANGUAGES
from src.wiki_app.metrics import (
    REPO_SUMMARIZATIONS_TOTAL, REPO_PROCESSING_DURATION, STEP_DURATION, STEP_COMPLETED,
    FILES_PROCESSED_TOTAL, FILE_SUMMARIZATION_DURATION, FOLDERS_PROCESSED_TOTAL,
    FOLDER_SUMMARIZATION_DURATION, GITHUB_API_CALLS_TOTAL, GITHUB_API_DURATION,
    REPOS_PROCESSING
)
from src.wiki_app.progress import ProgressTracker, ProcessingContext, should_resume
from loguru import logger

MAX_FILES_ALLOWED = 600

class InsertRepoService:
    def __init__(self, llm_provider: LLMProvider, repo_provider: Optional[RepoProvider] = None):
        # Note: This service is instantiated per task, so it is not a singleton.
        # However, we use a semaphore to limit concurrent requests to GitHub/LLM to avoid rate limits.
        self.codeProcessor = CodeProcessor(llm_provider)
        self.folderProcessor = FolderProcessor(llm_provider)
        self.folderPathMap: Dict[str, int] = {}
        self.repoFileInfo: Optional[Dict[str, str]] = None
        self.semaphore = asyncio.Semaphore(20)  # Limit concurrent repo requests
        self.dependencyParser = DependencyParser()
        # Use provided repo_provider or get from factory
        self.repo_provider = repo_provider if repo_provider else get_repo_provider()

    async def insertRepository(self, owner: str, repo: str, force_restart: bool = False):
        # Track processing start
        REPOS_PROCESSING.inc()
        repo_start_time = time.time()

        # Create processing context for structured logging
        context = ProcessingContext(owner, repo)
        context.info(f"Starting repository processing (force_restart={force_restart})")

        # Try to find existing repository record (created by views.py)
        repository = await Repository.objects.filter(owner=owner, repo=repo).afirst()
        if not repository:
            # Fallback: create with GitHub URL format
            repo_url = f"https://github.com/{owner}/{repo}"
            repository, _ = await Repository.objects.aupdate_or_create(
                url=repo_url,
                defaults={
                    'owner': owner,
                    'repo': repo,
                    'default_branch': 'main',
                    'process_status': f"Starting processing for {owner}/{repo}..."
                }
            )
        else:
            # Update status on existing record
            repository.process_status = f"Starting processing for {owner}/{repo}..."
            await repository.asave(update_fields=['process_status'])

        # Check if we should resume from checkpoint
        resuming = should_resume(repository, force_restart)
        if resuming:
            context.info("Resuming from checkpoint")
        elif force_restart and repository.processing_state:
            context.info("Force restart requested, clearing previous state")
            repository.processing_state = {}
            repository.processing_status = 'pending'
            await repository.asave(update_fields=['processing_state', 'processing_status'])

        # Initialize progress tracker
        tracker = ProgressTracker(repository, context)
        tracker.set_resuming(resuming)

        # Get completed items for resume
        completed_files: Set[str] = set()
        completed_folders: Set[str] = set()
        if resuming:
            completed_files = tracker.checkpoint.get_completed_files()
            completed_folders = tracker.checkpoint.get_completed_folders()
            context.info(f"Resume state: {len(completed_files)} files, {len(completed_folders)} folders completed")

        async def update_status(msg: str):
            context.info(msg)
            repository.process_status = msg
            await repository.asave(update_fields=['process_status'])

        try:
            # Initialize checkpoint manager
            tracker.checkpoint.initialize_state(resuming=resuming)

            # Step 1: Fetch repo details
            step_start = time.time()
            await tracker.step_start('fetch_details', message=f"Fetching repository details for {owner}/{repo}...")
            repo_details = await self.repo_provider.get_details(owner, repo)
            STEP_DURATION.labels(step='fetch_details').observe(time.time() - step_start)
            STEP_COMPLETED.labels(step='fetch_details', status='success').inc()
            GITHUB_API_CALLS_TOTAL.labels(endpoint='repo_details', status='success').inc()
            await tracker.step_complete('fetch_details', items_processed=1)

            if repo_details.language and repo_details.language not in ALLOWED_LANGUAGES:
                await update_status(f"Language {repo_details.language} not supported. Skipping.")
                REPO_SUMMARIZATIONS_TOTAL.labels(owner=owner, repo=repo, status='skipped').inc()
                return None

            # Step 2: Insert repository
            step_start = time.time()
            await tracker.step_start('insert_repo', message=f"Inserting repository {repo_details.repo_owner}/{repo_details.repo_name} into DB...")

            # Upsert Repository
            repository, created = await Repository.objects.aupdate_or_create(
                url=repo_details.url,
                defaults={
                    'owner': repo_details.repo_owner,
                    'repo': repo_details.repo_name,
                    'language': repo_details.language,
                    'descriptions': repo_details.description,
                    'default_branch': repo_details.default_branch,
                    'stars': repo_details.stars,
                    'forks': repo_details.forks,
                    'process_status': "Updating repository details...",
                    'processing_status': 'in_progress'
                }
            )

            # Re-initialize tracker with updated repository
            tracker = ProgressTracker(repository, context)
            tracker.set_resuming(resuming)

            # Handle Topics
            for topic_name in repo_details.topics:
                topic, _ = await Topic.objects.aget_or_create(topic_name=topic_name)
                await repository.topics.aadd(topic)

            if not created:
                context.info(f"Repository updated: {owner}/{repo}")
            STEP_DURATION.labels(step='insert_repo').observe(time.time() - step_start)
            STEP_COMPLETED.labels(step='insert_repo', status='success').inc()
            await tracker.step_complete('insert_repo', items_processed=1)

            # Step 3: Insert branch
            step_start = time.time()
            await tracker.step_start('insert_branch', message=f"Inserting branch {repo_details.default_branch} into DB...")
            branch, _ = await Branch.objects.aget_or_create(
                repository=repository,
                last_commit_sha=repo_details.sha,
                defaults={
                    'name': repo_details.default_branch,
                    'commit_at': repo_details.commit_at,
                }
            )
            STEP_DURATION.labels(step='insert_branch').observe(time.time() - step_start)
            STEP_COMPLETED.labels(step='insert_branch', status='success').inc()
            await tracker.step_complete('insert_branch', items_processed=1)

            self.repoFileInfo = {
                "repo_owner": owner,
                "repo_name": repo,
                "commit_sha": repo_details.sha
            }

            # Step 4: Fetch repo tree
            step_start = time.time()
            await tracker.step_start('fetch_tree', message=f"Fetching entire repo tree for {owner}/{repo} @ {repo_details.sha}...")
            fullTree = await self.repo_provider.get_tree(owner, repo, repo_details.sha)
            STEP_DURATION.labels(step='fetch_tree').observe(time.time() - step_start)
            STEP_COMPLETED.labels(step='fetch_tree', status='success').inc()
            GITHUB_API_CALLS_TOTAL.labels(endpoint='repo_tree', status='success').inc()
            context.info(f"Fetched repo tree in {time.time() - step_start:.2f}s")
            await tracker.step_complete('fetch_tree', items_processed=1)

            # Step 5: Filter tree
            step_start = time.time()
            await tracker.step_start('filter', message="Filtering tree in memory...")
            filteredTree = self._filterTree(fullTree)
            STEP_DURATION.labels(step='filter_tree').observe(time.time() - step_start)
            STEP_COMPLETED.labels(step='filter_tree', status='success').inc()
            await tracker.step_complete('filter', items_processed=1)

            # Guardrail: skip summarization for very large repositories
            total_files = self._count_files(filteredTree)
            total_folders = self._count_folders(filteredTree)

            if total_files > MAX_FILES_ALLOWED:
                skip_msg = (
                    f"This repository requires too much tokens, try with smaller file. "
                    f"Repository has {total_files} files, exceeding the limit of {MAX_FILES_ALLOWED}. "
                    "Summarization skipped."
                )
                await update_status(skip_msg)
                await Branch.objects.filter(branch_id=branch.branch_id).aupdate(ai_summary=skip_msg)
                REPO_SUMMARIZATIONS_TOTAL.labels(owner=owner, repo=repo, status='skipped').inc()
                REPO_PROCESSING_DURATION.labels(owner=owner, repo=repo).observe(time.time() - repo_start_time)
                return repository

            # Step 6: Insert folders
            step_start = time.time()
            await tracker.step_start('insert_folders', total=total_folders, message="Inserting folder structure into DB...")
            await self._insertFolders(filteredTree, branch, None)
            STEP_DURATION.labels(step='insert_folders').observe(time.time() - step_start)
            STEP_COMPLETED.labels(step='insert_folders', status='success').inc()
            await tracker.step_complete('insert_folders', items_processed=total_folders)

            # Step 7: Fetch files and summarize
            await tracker.step_start('summarize_files', total=total_files, message="Fetching files and summarizing...")
            folder_progress = [0]  # Shared counter for folder progress
            folder_ready_events = {path: asyncio.Event() for path in self.folderPathMap.keys()}

            step_start = time.time()
            folder_summary_task = asyncio.create_task(
                self._summarizeFolders(
                    filteredTree,
                    tracker,
                    folder_progress,
                    depth=0,
                    folder_ready_events=folder_ready_events,
                    completed_folders=completed_folders
                )
            )

            files_start = time.time()
            await self._fetchAndInsertFiles(filteredTree, tracker, folder_ready_events, completed_files)
            STEP_DURATION.labels(step='summarize_files').observe(time.time() - files_start)
            STEP_COMPLETED.labels(step='summarize_files', status='success').inc()
            context.info(f"Fetched and inserted files in {time.time() - files_start:.2f}s")
            await tracker.step_complete('summarize_files', items_processed=tracker.files_processed, items_failed=tracker.files_failed)

            repo_summary = await folder_summary_task
            STEP_DURATION.labels(step='summarize_folders').observe(time.time() - step_start)
            STEP_COMPLETED.labels(step='summarize_folders', status='success').inc()
            context.info(f"Summarized folders in {time.time() - step_start:.2f}s")
            await tracker.step_complete('summarize_folders', items_processed=tracker.folders_processed, items_failed=tracker.folders_failed)

            # Store repo-level summary on the branch so the UI can detect completion
            if repo_summary:
                await Branch.objects.filter(branch_id=branch.branch_id).aupdate(
                    ai_summary=repo_summary
                )

            await tracker.complete("Done! Repository processed successfully.")

            # Record success metrics
            REPO_SUMMARIZATIONS_TOTAL.labels(owner=owner, repo=repo, status='success').inc()
            REPO_PROCESSING_DURATION.labels(owner=owner, repo=repo).observe(time.time() - repo_start_time)

            return repository

        except Exception as e:
            context.error(f"Failed to process repository: {e}")
            await tracker.error('processing', str(e))
            REPO_SUMMARIZATIONS_TOTAL.labels(owner=owner, repo=repo, status='failed').inc()
            raise
        finally:
            REPOS_PROCESSING.dec()

    def _filterTree(self, tree: RepoTreeResult) -> RepoTreeResult:
        logger.info(f'Filtering tree at path "{tree.path or "/"}"...')
        allowed_files = whitelisted_file(tree.files, whitelisted_filter)
        allowed_files = blacklisted_files(allowed_files, blacklisted_file)
        allowed_subdirs = blacklisted_folder(tree.subdirectories, blacklisted_filter)
        pruned_subdirs = []
        for subdir in allowed_subdirs:
            filtered_subdir = self._filterTree(subdir)
            if filtered_subdir.files or filtered_subdir.subdirectories:
                pruned_subdirs.append(filtered_subdir)
        return RepoTreeResult(path=tree.path, files=allowed_files, subdirectories=pruned_subdirs)

    async def _insertFolders(self, tree: RepoTreeResult, branch: Branch, parent_folder: Optional[Folder]):
        folder_name = tree.path.split("/")[-1] if tree.path else ""
        folder_path = tree.path

        logger.info(f'\tInserting folder "{folder_name}" with path "{folder_path}"...')
        
        folder, _ = await Folder.objects.aget_or_create(
            path=folder_path,
            branch=branch,
            defaults={
                'name': folder_name,
                'parent_folder': parent_folder
            }
        )
        
        self.folderPathMap[folder_path] = folder.folder_id

        for subdir in tree.subdirectories:
            await self._insertFolders(subdir, branch, folder)

    def _count_files(self, tree: RepoTreeResult) -> int:
        count = len(tree.files)
        for subdir in tree.subdirectories:
            count += self._count_files(subdir)
        return count

    def _count_folders(self, tree: RepoTreeResult) -> int:
        count = 1  # Count this folder
        for subdir in tree.subdirectories:
            count += self._count_folders(subdir)
        return count

    async def _fetchAndInsertFiles(
        self,
        rootTree: RepoTreeResult,
        tracker: Optional[ProgressTracker] = None,
        folder_ready_events: Optional[Dict[str, asyncio.Event]] = None,
        completed_files: Optional[Set[str]] = None
    ):
        completed_files = completed_files or set()
        all_file_paths = []

        def gather_files(t: RepoTreeResult):
            all_file_paths.extend(t.files)
            for s in t.subdirectories:
                gather_files(s)
        gather_files(rootTree)

        # Filter out already completed files for resume
        files_to_process = [fp for fp in all_file_paths if fp not in completed_files]
        skipped_count = len(all_file_paths) - len(files_to_process)

        if tracker:
            if skipped_count > 0:
                await tracker.step_progress(skipped_count, message=f"Skipping {skipped_count} already processed files...")
            await tracker.step_progress(0, message=f"Found {len(files_to_process)} files to process...")

        progress_counter = skipped_count  # Start from skipped count for resume
        progress_lock = asyncio.Lock()
        total_files = len(all_file_paths)

        async def fetch_content(fp: str, session: aiohttp.ClientSession):
            if not self.repoFileInfo:
                logger.error("repoFileInfo is None")
                return fp, None

            async with self.semaphore:
                try:
                    content = await self.repo_provider.get_file_content(
                        self.repoFileInfo["repo_owner"],
                        self.repoFileInfo["repo_name"],
                        self.repoFileInfo["commit_sha"],
                        fp,
                        session
                    )
                    return fp, content
                except Exception as e:
                    logger.error(f"\tFailed fetching file: {fp}, error: {e}")
                    return fp, None

        async def summarize_file(file_path: str, content: Optional[str]):
            nonlocal progress_counter
            file_start_time = time.time()

            if not content:
                FILES_PROCESSED_TOTAL.labels(status='skipped').inc()
                if tracker:
                    await tracker.file_processed(file_path, success=False, duration=0)
                return None

            # Parse dependencies from the file content
            dependencies = self.dependencyParser.parse(content, file_path)

            aiSummary = None
            retries = 0
            wordDeduction = 0
            while not aiSummary and retries < TokenProcessingConfig['maxRetries']:
                try:
                    slice_size = TokenProcessingConfig['characterLimit'] - wordDeduction
                    reducedContent = content[: max(0, slice_size)]
                    aiSummary = await self.codeProcessor.generate(reducedContent, {
                        "path": file_path,
                        **(self.repoFileInfo or {})
                    })
                except Exception:
                    pass
                finally:
                    retries += 1
                    wordDeduction += TokenProcessingConfig['reduceCharPerRetry']

            duration = time.time() - file_start_time

            # Record file metrics
            FILE_SUMMARIZATION_DURATION.observe(duration)
            success = aiSummary is not None
            if success:
                FILES_PROCESSED_TOTAL.labels(status='success').inc()
            else:
                FILES_PROCESSED_TOTAL.labels(status='failed').inc()

            # Update progress via tracker
            async with progress_lock:
                progress_counter += 1
                if tracker:
                    await tracker.file_processed(file_path, success=success, duration=duration)
                    if progress_counter % 5 == 0:
                        await tracker.step_progress(progress_counter, current=file_path)

            return {"filePath": file_path, "content": content, "aiSummary": aiSummary, "dependencies": dependencies}

        async def process_files_for_folder(file_paths: List[str], folder_path: str, session: aiohttp.ClientSession):
            folder_event = folder_ready_events.get(folder_path) if folder_ready_events is not None else None

            # Filter files for this folder that need processing
            files_for_folder = [fp for fp in file_paths if fp not in completed_files]

            if not files_for_folder:
                if folder_event:
                    folder_event.set()
                return

            try:
                async def process_single_file(fp):
                    _, content = await fetch_content(fp, session)
                    return await summarize_file(fp, content)

                tasks = [process_single_file(fp) for fp in files_for_folder]
                processed_files = await asyncio.gather(*tasks)

                files_to_create = []
                for f in processed_files:
                    if not f or not f["aiSummary"]:
                        continue
                    file_path = f["filePath"]
                    folder_id = self.folderPathMap.get(folder_path)
                    if not folder_id:
                        continue

                    file_name = file_path.split("/")[-1]

                    files_to_create.append(File(
                        name=file_name,
                        folder_id=folder_id,
                        content=f["content"],
                        ai_summary=f["aiSummary"].summary,
                        usage=f["aiSummary"].usage,
                        dependencies=f.get("dependencies", [])
                    ))

                if files_to_create:
                    await File.objects.abulk_create(files_to_create)
            finally:
                if folder_event:
                    folder_event.set()

        async def process_folder(tree: RepoTreeResult, session: aiohttp.ClientSession):
            folder_path = tree.path
            file_task = asyncio.create_task(process_files_for_folder(tree.files, folder_path, session))
            sub_tasks = [asyncio.create_task(process_folder(sub, session)) for sub in tree.subdirectories]
            await asyncio.gather(file_task, *sub_tasks)

        async with aiohttp.ClientSession() as session:
            await process_folder(rootTree, session)

    async def _summarizeFolders(
        self,
        tree: RepoTreeResult,
        tracker: Optional[ProgressTracker] = None,
        folder_progress: Optional[List[int]] = None,
        depth: int = 0,
        folder_ready_events: Optional[Dict[str, asyncio.Event]] = None,
        completed_folders: Optional[Set[str]] = None
    ) -> Optional[str]:
        folder_name = tree.path or "/"
        completed_folders = completed_folders or set()

        # Parallelize subfolder summarization: Spawn tasks for all subdirectories immediately
        # so they can proceed independently as soon as their files are ready.
        tasks = [
            asyncio.create_task(
                self._summarizeFolders(
                    subdir, tracker, folder_progress, depth + 1,
                    folder_ready_events, completed_folders
                )
            )
            for subdir in tree.subdirectories
        ]
        subfolders_future = asyncio.gather(*tasks) if tasks else None

        waitables = []
        if subfolders_future:
            waitables.append(subfolders_future)

        folder_event = None
        if folder_ready_events is not None:
            folder_event = folder_ready_events.get(tree.path)
            if folder_event:
                waitables.append(folder_event.wait())

        if waitables:
            await asyncio.gather(*waitables)

        subfolders_summaries_results = subfolders_future.result() if subfolders_future else []

        subfolders_summaries = []
        for i, summary in enumerate(subfolders_summaries_results):
            if summary:
                subfolders_summaries.append(f"Summary of folder {tree.subdirectories[i].path}:\n{summary}\n")

        folder_id = self.folderPathMap.get(tree.path)
        if not folder_id:
            return None

        # Check if this folder was already completed (for resume)
        if tree.path in completed_folders:
            # Return existing summary from database
            folder_obj = await Folder.objects.filter(folder_id=folder_id).afirst()
            if folder_obj and folder_obj.ai_summary:
                return folder_obj.ai_summary

        files_in_folder = []
        async for f in File.objects.filter(folder_id=folder_id):
            files_in_folder.append(f)

        # Build file summaries with import information for LLM context
        file_summaries = []
        for f in files_in_folder:
            if f.ai_summary:
                summary_parts = [f"Summary of file {f.name}:\n{f.ai_summary}"]
                # Include import info to help LLM understand dependencies
                if f.dependencies:
                    summary_parts.append(f"Imports: {', '.join(f.dependencies[:10])}")  # Limit to avoid token overflow
                file_summaries.append("\n".join(summary_parts) + "\n")

        if not subfolders_summaries and not file_summaries:
            return None

        folder_start_time = time.time()

        # Combine all context for the LLM
        combined_parts = subfolders_summaries + file_summaries
        combined = "\n\n".join(combined_parts)

        aiSummary = None
        retries = 0
        summaryDeduction = 0
        while not aiSummary and retries < TokenProcessingConfig['maxRetries']:
            try:
                slice_size = TokenProcessingConfig['characterLimit'] - summaryDeduction
                reduced = combined[: max(0, slice_size)]
                aiSummary = await self.folderProcessor.generate([reduced], {
                    "path": tree.path,
                    **(self.repoFileInfo or {})
                })
            except Exception:
                pass
            finally:
                retries += 1
                summaryDeduction += TokenProcessingConfig['reduceCharPerRetry']

        duration = time.time() - folder_start_time

        # Record folder metrics
        FOLDER_SUMMARIZATION_DURATION.observe(duration)
        if aiSummary:
            FOLDERS_PROCESSED_TOTAL.labels(status='success').inc()
        else:
            FOLDERS_PROCESSED_TOTAL.labels(status='failed').inc()
            return None

        # Use the LLM-generated dependency graph with descriptive relationship labels
        dependency_graph = aiSummary.dependency_graph if hasattr(aiSummary, 'dependency_graph') else None

        await Folder.objects.filter(folder_id=folder_id).aupdate(
            ai_summary=aiSummary.summary,
            usage=aiSummary.usage,
            dependency_graph=dependency_graph if dependency_graph else None
        )

        # Update progress via tracker
        if tracker:
            child_count = len(files_in_folder) + len(tree.subdirectories)
            await tracker.folder_processed(tree.path, child_count, duration)

        if folder_progress is not None:
            folder_progress[0] += 1

        return aiSummary.summary
