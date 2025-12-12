"""
Progress tracking, checkpoint management, and structured logging for repository processing.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any
import uuid
import time
import json
from loguru import logger


@dataclass
class ProgressEvent:
    """Structured progress event for SSE streaming."""
    type: str  # 'step_start', 'step_progress', 'step_complete', 'file_processed', 'folder_processed', 'error', 'complete'
    step: str  # 'fetch_details', 'fetch_tree', 'filter', 'insert_folders', 'summarize_files', 'summarize_folders'
    message: str  # Human-readable status
    current: Optional[str] = None  # Current file/folder being processed
    total: Optional[int] = None  # Total items in current step
    completed: Optional[int] = None  # Completed items in current step
    failed: Optional[int] = None  # Failed items in current step
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    resuming: bool = False  # Whether this is a resumed processing

    def to_json(self) -> str:
        """Convert to JSON string for SSE streaming."""
        return json.dumps(asdict(self))

    def to_dict(self) -> dict:
        """Convert to dict."""
        return asdict(self)


class ProcessingContext:
    """Structured logging context for a repository processing job."""

    def __init__(self, owner: str, repo: str):
        self.correlation_id = str(uuid.uuid4())[:8]
        self.owner = owner
        self.repo = repo
        self.start_time = time.time()
        self._step_timers: Dict[str, float] = {}

    def log(self, level: str, message: str, **kwargs):
        """Log with correlation context."""
        logger.bind(
            correlation_id=self.correlation_id,
            owner=self.owner,
            repo=self.repo,
            **kwargs
        ).log(level, f"[{self.correlation_id}] {self.owner}/{self.repo} - {message}")

    def debug(self, message: str, **kwargs):
        self.log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        self.log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        self.log("ERROR", message, **kwargs)

    def start_step(self, step: str):
        """Mark the start of a processing step."""
        self._step_timers[step] = time.time()
        self.info(f"Step started: {step}")

    def end_step(self, step: str, items_processed: int = 0, items_failed: int = 0):
        """Mark the end of a processing step and log timing."""
        duration = time.time() - self._step_timers.get(step, self.start_time)
        self.info(
            f"Step completed: {step} in {duration:.2f}s "
            f"(processed={items_processed}, failed={items_failed})",
            step=step,
            duration=duration,
            items_processed=items_processed,
            items_failed=items_failed
        )

    def log_file_processed(self, file_path: str, success: bool, duration: float):
        """Log individual file processing result."""
        status = "success" if success else "failed"
        self.debug(
            f"File {status}: {file_path} ({duration:.2f}s)",
            file_path=file_path,
            status=status,
            duration=duration
        )

    def log_folder_processed(self, folder_path: str, child_count: int, duration: float):
        """Log folder summarization result."""
        self.debug(
            f"Folder summarized: {folder_path} ({child_count} children, {duration:.2f}s)",
            folder_path=folder_path,
            child_count=child_count,
            duration=duration
        )

    def log_summary(self, files_processed: int, files_failed: int, folders_processed: int, folders_failed: int):
        """Log final processing summary."""
        total_duration = time.time() - self.start_time
        self.info(
            f"Processing complete in {total_duration:.2f}s: "
            f"files={files_processed}/{files_processed + files_failed}, "
            f"folders={folders_processed}/{folders_processed + folders_failed}",
            total_duration=total_duration,
            files_processed=files_processed,
            files_failed=files_failed,
            folders_processed=folders_processed,
            folders_failed=folders_failed
        )


class CheckpointManager:
    """Manages processing state persistence for checkpoint/resume functionality."""

    BATCH_SIZE = 10  # Save checkpoint every N files

    def __init__(self, repository):
        self.repository = repository
        self._pending_files: List[str] = []
        self._pending_folders: List[str] = []
        self._last_save_time = time.time()

    def get_state(self) -> Dict[str, Any]:
        """Get current processing state."""
        return self.repository.processing_state or {}

    def initialize_state(self, total_files: int = 0, total_folders: int = 0, resuming: bool = False):
        """Initialize or reset processing state."""
        if resuming and self.repository.processing_state:
            # Keep existing state, just update status
            state = self.repository.processing_state
            state['status'] = 'in_progress'
            state['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        else:
            state = {
                'status': 'in_progress',
                'current_step': 'fetch_details',
                'steps_completed': [],
                'file_progress': {
                    'total': total_files,
                    'completed': 0,
                    'failed': 0,
                    'completed_paths': [],
                    'failed_paths': []
                },
                'folder_progress': {
                    'total': total_folders,
                    'completed': 0,
                    'failed': 0,
                    'completed_paths': []
                },
                'error': None,
                'started_at': datetime.utcnow().isoformat() + 'Z',
                'updated_at': datetime.utcnow().isoformat() + 'Z'
            }
        self.repository.processing_state = state
        self.repository.processing_status = 'in_progress'

    async def update_step(self, step: str, completed: bool = False):
        """Update current processing step."""
        state = self.get_state()
        state['current_step'] = step
        if completed and step not in state.get('steps_completed', []):
            state.setdefault('steps_completed', []).append(step)
        state['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        self.repository.processing_state = state
        await self.repository.asave(update_fields=['processing_state'])

    def mark_file_completed(self, file_path: str, success: bool = True):
        """Mark a file as completed (batched save)."""
        self._pending_files.append((file_path, success))
        if len(self._pending_files) >= self.BATCH_SIZE or (time.time() - self._last_save_time) > 30:
            return True  # Signal to save
        return False

    def mark_folder_completed(self, folder_path: str):
        """Mark a folder as completed."""
        self._pending_folders.append(folder_path)

    async def save_checkpoint(self):
        """Persist pending progress to database."""
        state = self.get_state()

        # Process pending files
        for file_path, success in self._pending_files:
            file_progress = state.setdefault('file_progress', {
                'total': 0, 'completed': 0, 'failed': 0,
                'completed_paths': [], 'failed_paths': []
            })
            if success:
                file_progress['completed'] = file_progress.get('completed', 0) + 1
                # Limit stored paths to last 100 to avoid huge JSON
                if len(file_progress.get('completed_paths', [])) < 100:
                    file_progress.setdefault('completed_paths', []).append(file_path)
            else:
                file_progress['failed'] = file_progress.get('failed', 0) + 1
                file_progress.setdefault('failed_paths', []).append(file_path)
        self._pending_files = []

        # Process pending folders
        for folder_path in self._pending_folders:
            folder_progress = state.setdefault('folder_progress', {
                'total': 0, 'completed': 0, 'failed': 0, 'completed_paths': []
            })
            folder_progress['completed'] = folder_progress.get('completed', 0) + 1
            folder_progress.setdefault('completed_paths', []).append(folder_path)
        self._pending_folders = []

        state['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        self.repository.processing_state = state
        await self.repository.asave(update_fields=['processing_state'])
        self._last_save_time = time.time()

    async def mark_completed(self):
        """Mark processing as completed."""
        await self.save_checkpoint()  # Save any pending
        state = self.get_state()
        state['status'] = 'completed'
        state['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        self.repository.processing_state = state
        self.repository.processing_status = 'completed'
        await self.repository.asave(update_fields=['processing_state', 'processing_status'])

    async def mark_failed(self, error: str):
        """Mark processing as failed."""
        await self.save_checkpoint()  # Save any pending progress
        state = self.get_state()
        state['status'] = 'failed'
        state['error'] = error
        state['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        self.repository.processing_state = state
        self.repository.processing_status = 'failed'
        await self.repository.asave(update_fields=['processing_state', 'processing_status'])

    def get_completed_files(self) -> set:
        """Get set of already completed file paths for resume."""
        state = self.get_state()
        file_progress = state.get('file_progress', {})
        return set(file_progress.get('completed_paths', []))

    def get_completed_folders(self) -> set:
        """Get set of already completed folder paths for resume."""
        state = self.get_state()
        folder_progress = state.get('folder_progress', {})
        return set(folder_progress.get('completed_paths', []))


class ProgressTracker:
    """Tracks and emits progress events during repository processing."""

    def __init__(
        self,
        repository,
        context: Optional[ProcessingContext] = None,
        on_progress: Optional[Callable[[ProgressEvent], None]] = None
    ):
        self.repository = repository
        self.context = context or ProcessingContext(repository.owner, repository.repo)
        self.checkpoint = CheckpointManager(repository)
        self._on_progress = on_progress
        self._current_step: str = ''
        self._step_total: int = 0
        self._step_completed: int = 0
        self._step_failed: int = 0
        self._resuming: bool = False

        # Cumulative counters
        self.files_processed: int = 0
        self.files_failed: int = 0
        self.folders_processed: int = 0
        self.folders_failed: int = 0

    def set_resuming(self, resuming: bool):
        """Set whether this is a resumed processing."""
        self._resuming = resuming

    def _emit(self, event: ProgressEvent):
        """Emit a progress event."""
        if self._on_progress:
            self._on_progress(event)

    async def step_start(self, step: str, total: Optional[int] = None, message: Optional[str] = None):
        """Signal the start of a processing step."""
        self._current_step = step
        self._step_total = total or 0
        self._step_completed = 0
        self._step_failed = 0

        self.context.start_step(step)
        await self.checkpoint.update_step(step)

        msg = message or f"Starting {step}..."
        self._emit(ProgressEvent(
            type='step_start',
            step=step,
            message=msg,
            total=total,
            completed=0,
            resuming=self._resuming
        ))

        # Update repository status
        self.repository.process_status = msg
        await self.repository.asave(update_fields=['process_status'])

    async def step_progress(self, completed: int, current: Optional[str] = None, message: Optional[str] = None):
        """Update progress within a step."""
        self._step_completed = completed
        msg = message or f"Processing {self._current_step}: {completed}/{self._step_total}"

        self._emit(ProgressEvent(
            type='step_progress',
            step=self._current_step,
            message=msg,
            current=current,
            total=self._step_total,
            completed=completed,
            failed=self._step_failed,
            resuming=self._resuming
        ))

        # Update repository status periodically
        if completed % 5 == 0 or current:
            self.repository.process_status = msg
            await self.repository.asave(update_fields=['process_status'])

    async def step_complete(self, step: str, items_processed: int = 0, items_failed: int = 0, message: Optional[str] = None):
        """Signal completion of a processing step."""
        self.context.end_step(step, items_processed, items_failed)
        await self.checkpoint.update_step(step, completed=True)

        msg = message or f"Completed {step}"
        self._emit(ProgressEvent(
            type='step_complete',
            step=step,
            message=msg,
            total=items_processed + items_failed,
            completed=items_processed,
            failed=items_failed,
            resuming=self._resuming
        ))

    async def file_processed(self, file_path: str, success: bool, duration: float):
        """Record a file processing result."""
        if success:
            self.files_processed += 1
            self._step_completed += 1
        else:
            self.files_failed += 1
            self._step_failed += 1

        self.context.log_file_processed(file_path, success, duration)

        # Batch checkpoint saves
        should_save = self.checkpoint.mark_file_completed(file_path, success)
        if should_save:
            await self.checkpoint.save_checkpoint()

        self._emit(ProgressEvent(
            type='file_processed',
            step='summarize_files',
            message=f"{'Processed' if success else 'Failed'}: {file_path}",
            current=file_path,
            total=self._step_total,
            completed=self._step_completed,
            failed=self._step_failed,
            resuming=self._resuming
        ))

    async def folder_processed(self, folder_path: str, child_count: int, duration: float, success: bool = True):
        """Record a folder summarization result."""
        if success:
            self.folders_processed += 1
        else:
            self.folders_failed += 1

        self.context.log_folder_processed(folder_path, child_count, duration)
        self.checkpoint.mark_folder_completed(folder_path)

        self._emit(ProgressEvent(
            type='folder_processed',
            step='summarize_folders',
            message=f"Summarized folder: {folder_path}",
            current=folder_path,
            resuming=self._resuming
        ))

    async def error(self, step: str, error_message: str):
        """Record an error."""
        self.context.error(f"Error in {step}: {error_message}")
        await self.checkpoint.mark_failed(error_message)

        self._emit(ProgressEvent(
            type='error',
            step=step,
            message=error_message,
            resuming=self._resuming
        ))

    async def complete(self, message: str = "Processing complete"):
        """Signal processing completion."""
        self.context.log_summary(
            self.files_processed, self.files_failed,
            self.folders_processed, self.folders_failed
        )
        await self.checkpoint.mark_completed()

        self._emit(ProgressEvent(
            type='complete',
            step='done',
            message=message,
            resuming=self._resuming
        ))

        self.repository.process_status = message
        await self.repository.asave(update_fields=['process_status'])


def should_resume(repository, force_restart: bool = False) -> bool:
    """Determine if processing should resume from checkpoint."""
    if force_restart:
        return False
    if not repository.processing_state:
        return False
    state = repository.processing_state
    status = state.get('status')
    if status in ['completed', 'pending', None]:
        return False
    if status in ['in_progress', 'failed', 'paused']:
        return True
    return False
