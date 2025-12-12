from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .tasks import run_repository_task
from .models import Repository, Branch, Folder, File
from .progress import should_resume, ProgressEvent
import time
import json
import os
import hashlib
import re
from typing import Generator, Optional, Tuple, Dict, Any

FILE_RETURN_LIMIT = 600

def _get_latest_branch(repository: Repository) -> Branch | None:
    """
    Return the most recent branch for a repository.
    If none found, try to recover via folders/files.
    """
    # Type annotation to help Pylance understand the relationship
    branch = repository.branches.order_by('-created_at').first()  # type: ignore
    if branch:
        return branch

    folder = Folder.objects.filter(branch__repository=repository).select_related('branch').order_by('-branch__created_at').first()
    if folder:
        return folder.branch

    file_obj = File.objects.filter(folder__branch__repository=repository).select_related('folder__branch').order_by('-folder__branch__created_at').first()
    if file_obj:
        return file_obj.folder.branch

    return None


def _is_repo_complete(repository: Repository, branch: Branch | None) -> bool:
    """
    Determine if a repository should be considered complete for rendering.
    Large repos may not store a branch-level summary even when processing is done.
    """
    if not branch:
        return False
    if branch.ai_summary:
        return True
    status_text = (repository.process_status or "").lower()
    if status_text.startswith("done"):
        return True
    # Self-healing: if we have persisted folders or files, consider it usable
    if Folder.objects.filter(branch=branch).exists() or File.objects.filter(folder__branch=branch).exists():
        return True
    return False

def index(request):
    return render(request, 'index.html')

def search(request):
    query = request.GET.get('q', '').strip()
    source_type = request.GET.get('source_type', '').strip()
    
    if not query:
        return redirect('index')
    
    # Import here to avoid circular imports
    from .utils import detect_source_type
    
    # Detect source type
    detected_type, parsed_info = detect_source_type(query, source_type if source_type else None)
    
    if detected_type == 'unknown':
        error_msg = parsed_info.get('error', 'Invalid input format')
        return render(request, 'index.html', {'error': error_msg})
    
    if detected_type == 'github':
        return _handle_github_source(request, parsed_info['owner'], parsed_info['repo'])
    elif detected_type == 'local':
        return _handle_local_source(request, parsed_info['path'])
    elif detected_type == 'git':
        return _handle_git_source(request, parsed_info['url'])
    else:
        return render(request, 'index.html', {'error': 'Unsupported source type'})


def _handle_github_source(request, owner: str, repo: str):
    """Handle GitHub repository source."""
    # Check if exists
    if Repository.objects.filter(owner=owner, repo=repo).exists():
        return redirect('repo_detail', owner=owner, repo=repo)
    
    # Create placeholder for queue tracking
    Repository.objects.create(
        url=f"https://github.com/{owner}/{repo}",
        owner=owner,
        repo=repo,
        default_branch='main',
        process_status='Queued'
    )

    # Trigger task (async or sync depending on Celery availability)
    result = run_repository_task(owner, repo, source_type='github')
    
    return render(request, 'processing.html', {
        'owner': owner,
        'repo': repo,
        'task_id': result.get('task_id'),
        'sync_mode': result['mode'] == 'sync'
    })


def _handle_local_source(request, path: str):
    """Handle local folder source."""
    import os
    import hashlib
    
    # Validate path exists
    if not os.path.exists(path):
        return render(request, 'index.html', {'error': f'Path does not exist: {path}'})
    
    if not os.path.isdir(path):
        return render(request, 'index.html', {'error': f'Path is not a directory: {path}'})
    
    # Generate owner/repo from path
    folder_name = os.path.basename(path.rstrip('/'))
    local_url = f"local://{path}"
    
    # First, check if this exact path was scanned before
    existing_by_url = Repository.objects.filter(url=local_url).first()
    if existing_by_url:
        return redirect('repo_detail', owner=existing_by_url.owner, repo=existing_by_url.repo)
    
    # Generate unique repo name based on path hash to avoid conflicts
    path_hash = hashlib.md5(path.encode()).hexdigest()[:8]
    owner = 'local'
    repo = f"{folder_name}_{path_hash}"
    
    # Create placeholder
    Repository.objects.create(
        url=local_url,
        owner=owner,
        repo=repo,
        default_branch='main',
        process_status='Queued'
    )

    # Trigger task
    result = run_repository_task(owner, repo, source_type='local', source_path=path)
    
    return render(request, 'processing.html', {
        'owner': owner,
        'repo': repo,
        'task_id': result.get('task_id'),
        'sync_mode': result['mode'] == 'sync'
    })


def _handle_git_source(request, url: str):
    """Handle generic Git URL source."""
    import re
    import hashlib
    
    # Extract repo name from URL
    # Examples: https://gitlab.com/owner/repo, git@gitlab.com:owner/repo.git
    url_clean = url.rstrip('/').rstrip('.git')
    
    # Try to extract owner/repo from URL
    match = re.search(r'[:/]([^/:]+)/([^/:]+)(?:\.git)?$', url_clean)
    if match:
        owner = match.group(1)
        repo = match.group(2)
    else:
        # Fallback: use hash of URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        owner = 'git'
        repo = f"repo_{url_hash}"
    
    # Check if exists
    existing = Repository.objects.filter(owner=owner, repo=repo).first()
    if existing:
        if existing.url == url:
            return redirect('repo_detail', owner=owner, repo=repo)
        # Different URL, make unique
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        repo = f"{repo}_{url_hash}"
    
    # Create placeholder
    Repository.objects.create(
        url=url,
        owner=owner,
        repo=repo,
        default_branch='main',
        process_status='Queued'
    )

    # Trigger task
    result = run_repository_task(owner, repo, source_type='git', source_path=url)
    
    return render(request, 'processing.html', {
        'owner': owner,
        'repo': repo,
        'task_id': result.get('task_id'),
        'sync_mode': result['mode'] == 'sync'
    })

def repo_detail(request, owner, repo):
    from django.http import Http404
    repository = Repository.objects.filter(owner=owner, repo=repo).first()
    if not repository:
        raise Http404("Repository not found")
    
    # Get the latest branch
    branch = _get_latest_branch(repository)
    
    # Check if processing is complete (summary or explicit done status)
    if not _is_repo_complete(repository, branch):
        # If not ready, render processing page
        return render(request, 'processing.html', {
            'owner': owner,
            'repo': repo,
            'task_id': None # We don't have task ID here easily, but that's fine for polling
        })
    
    file_qs = File.objects.filter(folder__branch=branch)
    # Only inspect a small sample to decide if we should include files; avoid loading large file sets
    sampled_ids = list(file_qs.values_list('file_id', flat=True)[: FILE_RETURN_LIMIT + 1])
    include_files = len(sampled_ids) <= FILE_RETURN_LIMIT
    total_files = len(sampled_ids) if include_files else None

    # Build file tree
    file_tree = build_tree(branch, include_files=include_files)
    
    return render(request, 'repo.html', {
        'repository': repository,
        'branch': branch,
        'file_tree': file_tree,
        'files_omitted': not include_files,
        'total_files': total_files,
        'file_return_limit': FILE_RETURN_LIMIT
    })

def build_tree(branch, include_files=True):
    folders = Folder.objects.filter(branch=branch).select_related('parent_folder')
    files = File.objects.none()
    if include_files:
        files = File.objects.filter(folder__branch=branch).select_related('folder')
    
    # Map folder_id -> node
    folder_nodes = {}
    for f in folders:
        folder_nodes[f.folder_id] = {
            'type': 'folder',
            'obj': f,
            'children': [], # List of folder nodes or file nodes
            'is_root': f.path == ""
        }
        
    # Add files to folder nodes
    for f in files:
        if f.folder_id in folder_nodes:  # type: ignore
            folder_nodes[f.folder_id]['children'].append({  # type: ignore
                'type': 'file',
                'obj': f
            })
            
    # Build hierarchy
    roots = []
    for f in folders:
        node = folder_nodes[f.folder_id]
        if f.parent_folder_id:  # type: ignore
            parent = folder_nodes.get(f.parent_folder_id)  # type: ignore
            if parent:
                parent['children'].append(node)
            else:
                roots.append(node) # Orphaned? Treat as root
        else:
            roots.append(node)
            
    # If we have a root folder (path=""), we want to return it as the top level
    # instead of flattening it.
    # And rename it to "/"
    for node in roots:
        if node['is_root']:
            node['obj'].name = "/"
            
    # Sort children by name (folders first?)
    def sort_node(node):
        if node['type'] == 'folder':
            node['children'].sort(key=lambda x: (x['type'] != 'folder', x['obj'].name))
            for child in node['children']:
                sort_node(child)
                
    for node in roots:
        sort_node(node)
        
    roots.sort(key=lambda x: (x['type'] != 'folder', x['obj'].name))
    
    return roots

def repo_status_stream(request, owner, repo):
    def event_stream():
        timeout_counter = 0
        max_retries_for_creation = 30  # Wait 60 seconds for the repo to be created

        while True:
            # Check if repository is processed
            try:
                # Force fresh read from DB (avoid cached results)
                from django.db import connection
                connection.close()
                # Use filter().first() to handle potential duplicates gracefully
                repository = Repository.objects.filter(owner=owner, repo=repo).first()
                if not repository:
                    raise Repository.DoesNotExist()
                branch = _get_latest_branch(repository)

                if _is_repo_complete(repository, branch):
                    # Send completion event
                    data = json.dumps({'status': 'complete'})
                    yield f"data: {data}\n\n".encode('utf-8')
                    break
                else:
                    # Send processing event with enhanced progress information
                    status_msg = repository.process_status or "Processing..."
                    start_time = repository.process_start_at.isoformat() if repository.process_start_at else None

                    # Calculate queue position if status is 'Queued'
                    queue_pos = None
                    if status_msg == 'Queued':
                        queue_pos = Repository.objects.filter(
                            process_status='Queued',
                            queued_at__lt=repository.queued_at
                        ).count() + 1

                    # Extract progress info from processing_state
                    processing_state = repository.processing_state or {}
                    file_progress = processing_state.get('file_progress', {})
                    folder_progress = processing_state.get('folder_progress', {})

                    event_data = {
                        'status': 'processing',
                        'message': status_msg,
                        'start_time': start_time,
                        'queue_pos': queue_pos,
                        'processing_status': repository.processing_status,
                        'current_step': processing_state.get('current_step'),
                        'resuming': processing_state.get('status') == 'in_progress' and bool(file_progress.get('completed', 0)),
                        'progress': {
                            'files': {
                                'total': file_progress.get('total', 0),
                                'completed': file_progress.get('completed', 0),
                                'failed': file_progress.get('failed', 0)
                            },
                            'folders': {
                                'total': folder_progress.get('total', 0),
                                'completed': folder_progress.get('completed', 0)
                            }
                        }
                    }

                    data = json.dumps(event_data)
                    yield f"data: {data}\n\n".encode('utf-8')
            except Repository.DoesNotExist:
                if timeout_counter > max_retries_for_creation:
                    data = json.dumps({'status': 'error', 'message': 'Repository initialization timed out or failed.'})
                    yield f"data: {data}\n\n".encode('utf-8')
                    break

                data = json.dumps({'status': 'processing', 'message': 'Initializing repository...'})
                yield f"data: {data}\n\n".encode('utf-8')
                timeout_counter += 1

            time.sleep(1)  # Check every 1 second for more responsive updates

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable buffering in Nginx
    return response

class RepositoryQueueView(APIView):
    def get(self, request):
        # For now, return empty queue status as we moved to Celery
        # We could implement Celery inspection here if needed
        return Response({
            "current": None,
            "queue": [],
            "time": None
        })

    def post(self, request):
        owner = request.data.get('owner')
        repo = request.data.get('repo')
        if not owner or not repo:
            return Response({"success": False, "message": "Owner and repo required"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if exists
        if Repository.objects.filter(owner=owner, repo=repo).exists():
             return Response({"success": False, "message": "Item already in database"}, status=status.HTTP_400_BAD_REQUEST)

        # Trigger task (async or sync depending on Celery availability)
        result = run_repository_task(owner, repo)
        return Response({
            "success": True,
            "message": f"Repository {owner}/{repo} added to queue",
            "task_id": result.get('task_id'),
            "mode": result['mode']
        }, status=status.HTTP_201_CREATED)


class RepositorySubmitView(APIView):
    """
    POST /api/repository/submit
    Submit a repository for processing with support for resume and progress tracking.
    """

    def post(self, request):
        source_type = request.data.get('source_type', '').strip()
        source_url = request.data.get('source_url', '').strip()
        force_restart = request.data.get('force_restart', False)

        if not source_url:
            return Response({
                "success": False,
                "message": "source_url is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Auto-detect source type if not provided
        from .utils import detect_source_type
        detected_type, parsed_info = detect_source_type(source_url, source_type if source_type else None)

        if detected_type == 'unknown':
            return Response({
                "success": False,
                "message": parsed_info.get('error', 'Invalid input format')
            }, status=status.HTTP_400_BAD_REQUEST)

        # Route to appropriate handler
        if detected_type == 'github':
            return self._handle_github(parsed_info['owner'], parsed_info['repo'], force_restart)
        elif detected_type == 'local':
            return self._handle_local(parsed_info['path'], force_restart)
        elif detected_type == 'git':
            return self._handle_git(parsed_info['url'], force_restart)
        else:
            return Response({
                "success": False,
                "message": "Unsupported source type"
            }, status=status.HTTP_400_BAD_REQUEST)

    def _handle_github(self, owner: str, repo: str, force_restart: bool) -> Response:
        """Handle GitHub repository submission."""
        existing = Repository.objects.filter(owner=owner, repo=repo).first()

        if existing:
            # Check if we should resume or redirect
            if should_resume(existing, force_restart):
                result = run_repository_task(owner, repo, source_type='github')
                return Response({
                    "success": True,
                    "owner": owner,
                    "repo": repo,
                    "status": "resuming",
                    "message": f"Resuming processing for {owner}/{repo}",
                    "task_id": result.get('task_id'),
                    "mode": result['mode'],
                    "processing_state": existing.processing_state
                }, status=status.HTTP_200_OK)
            elif existing.processing_status == 'completed':
                return Response({
                    "success": True,
                    "owner": owner,
                    "repo": repo,
                    "status": "completed",
                    "message": f"Repository {owner}/{repo} already processed",
                    "redirect_url": f"/{owner}/{repo}/"
                }, status=status.HTTP_200_OK)
            elif existing.processing_status == 'in_progress':
                return Response({
                    "success": True,
                    "owner": owner,
                    "repo": repo,
                    "status": "in_progress",
                    "message": f"Repository {owner}/{repo} is currently being processed",
                    "processing_state": existing.processing_state
                }, status=status.HTTP_200_OK)
            elif force_restart:
                # Force restart - clear state and re-process
                existing.processing_state = {}  # type: ignore
                existing.processing_status = 'pending'
                existing.process_status = 'Queued'
                existing.save()

        if not existing:
            # Create new repository record
            Repository.objects.create(
                url=f"https://github.com/{owner}/{repo}",
                owner=owner,
                repo=repo,
                default_branch='main',
                process_status='Queued',
                processing_status='pending'
            )

        # Trigger processing task
        result = run_repository_task(owner, repo, source_type='github', force_restart=force_restart)

        return Response({
            "success": True,
            "owner": owner,
            "repo": repo,
            "status": "queued",
            "message": f"Repository {owner}/{repo} queued for processing",
            "task_id": result.get('task_id'),
            "mode": result['mode']
        }, status=status.HTTP_201_CREATED)

    def _handle_local(self, path: str, force_restart: bool) -> Response:
        """Handle local folder submission."""
        # Validate path exists
        if not os.path.exists(path):
            return Response({
                "success": False,
                "message": f"Path does not exist: {path}"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not os.path.isdir(path):
            return Response({
                "success": False,
                "message": f"Path is not a directory: {path}"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Generate identifiers
        folder_name = os.path.basename(path.rstrip('/'))
        local_url = f"local://{path}"
        path_hash = hashlib.md5(path.encode()).hexdigest()[:8]
        owner = 'local'
        repo = f"{folder_name}_{path_hash}"

        # Check existing by URL
        existing = Repository.objects.filter(url=local_url).first()

        if existing:
            if should_resume(existing, force_restart):
                result = run_repository_task(existing.owner, existing.repo, source_type='local', source_path=path)
                return Response({
                    "success": True,
                    "owner": existing.owner,
                    "repo": existing.repo,
                    "status": "resuming",
                    "message": f"Resuming processing for {path}",
                    "task_id": result.get('task_id'),
                    "mode": result['mode'],
                    "processing_state": existing.processing_state
                }, status=status.HTTP_200_OK)
            elif existing.processing_status == 'completed':
                return Response({
                    "success": True,
                    "owner": existing.owner,
                    "repo": existing.repo,
                    "status": "completed",
                    "message": f"Local folder {path} already processed",
                    "redirect_url": f"/{existing.owner}/{existing.repo}/"
                }, status=status.HTTP_200_OK)
            elif existing.processing_status == 'in_progress':
                return Response({
                    "success": True,
                    "owner": existing.owner,
                    "repo": existing.repo,
                    "status": "in_progress",
                    "message": f"Local folder {path} is currently being processed",
                    "processing_state": existing.processing_state
                }, status=status.HTTP_200_OK)
            elif force_restart:
                existing.processing_state = {}  # type: ignore
                existing.processing_status = 'pending'
                existing.process_status = 'Queued'
                existing.save()
                owner = existing.owner
                repo = existing.repo

        if not existing:
            Repository.objects.create(
                url=local_url,
                owner=owner,
                repo=repo,
                default_branch='main',
                process_status='Queued',
                processing_status='pending'
            )

        result = run_repository_task(owner, repo, source_type='local', source_path=path, force_restart=force_restart)

        return Response({
            "success": True,
            "owner": owner,
            "repo": repo,
            "status": "queued",
            "message": f"Local folder {path} queued for processing",
            "task_id": result.get('task_id'),
            "mode": result['mode']
        }, status=status.HTTP_201_CREATED)

    def _handle_git(self, url: str, force_restart: bool) -> Response:
        """Handle generic Git URL submission."""
        url_clean = url.rstrip('/').rstrip('.git')

        # Extract owner/repo from URL
        match = re.search(r'[:/]([^/:]+)/([^/:]+)(?:\.git)?$', url_clean)
        if match:
            owner = match.group(1)
            repo = match.group(2)
        else:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            owner = 'git'
            repo = f"repo_{url_hash}"

        # Check existing by URL
        existing = Repository.objects.filter(url=url).first()
        if not existing:
            existing = Repository.objects.filter(owner=owner, repo=repo).first()

        if existing:
            if should_resume(existing, force_restart):
                result = run_repository_task(existing.owner, existing.repo, source_type='git', source_path=url)
                return Response({
                    "success": True,
                    "owner": existing.owner,
                    "repo": existing.repo,
                    "status": "resuming",
                    "message": f"Resuming processing for {url}",
                    "task_id": result.get('task_id'),
                    "mode": result['mode'],
                    "processing_state": existing.processing_state
                }, status=status.HTTP_200_OK)
            elif existing.processing_status == 'completed':
                return Response({
                    "success": True,
                    "owner": existing.owner,
                    "repo": existing.repo,
                    "status": "completed",
                    "message": f"Git repository {url} already processed",
                    "redirect_url": f"/{existing.owner}/{existing.repo}/"
                }, status=status.HTTP_200_OK)
            elif existing.processing_status == 'in_progress':
                return Response({
                    "success": True,
                    "owner": existing.owner,
                    "repo": existing.repo,
                    "status": "in_progress",
                    "message": f"Git repository {url} is currently being processed",
                    "processing_state": existing.processing_state
                }, status=status.HTTP_200_OK)
            elif force_restart:
                existing.processing_state = {}  # type: ignore
                existing.processing_status = 'pending'
                existing.process_status = 'Queued'
                existing.save()
                owner = existing.owner
                repo = existing.repo

        if not existing:
            # Handle potential conflict with different URL
            check_existing = Repository.objects.filter(owner=owner, repo=repo).first()
            if check_existing and check_existing.url != url:
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                repo = f"{repo}_{url_hash}"

            Repository.objects.create(
                url=url,
                owner=owner,
                repo=repo,
                default_branch='main',
                process_status='Queued',
                processing_status='pending'
            )

        result = run_repository_task(owner, repo, source_type='git', source_path=url, force_restart=force_restart)

        return Response({
            "success": True,
            "owner": owner,
            "repo": repo,
            "status": "queued",
            "message": f"Git repository {url} queued for processing",
            "task_id": result.get('task_id'),
            "mode": result['mode']
        }, status=status.HTTP_201_CREATED)
