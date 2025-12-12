# Design: Refactor Async Repository Processing

## Context

OpenRepoWiki processes repositories through a multi-step pipeline:
1. Fetch repository metadata
2. Fetch file tree
3. Filter tree (whitelist/blacklist)
4. Insert folder structure
5. Fetch files + summarize files (parallel)
6. Summarize folders (bottom-up, parallel)

Current implementation uses:
- Django views with GET request for submission
- Celery for async processing (or sync fallback)
- SSE (Server-Sent Events) for status polling
- `process_status` string field for status display

### Stakeholders
- End users: Need clear progress visibility and ability to resume interrupted processing
- Developers: Need detailed logs for debugging and monitoring
- System: Needs efficient checkpoint/resume to avoid wasting compute

## Goals / Non-Goals

### Goals
- RESTful API design for repository submission
- Granular, real-time progress tracking with file-level detail
- Checkpoint/resume capability for interrupted processing
- Structured logging with timing and correlation

### Non-Goals
- WebSocket implementation (SSE is sufficient)
- Multi-worker distributed processing
- Real-time UI updates for simultaneous viewers
- Historical progress retention beyond current job

## Decisions

### D1: Use POST for Repository Submission

**Decision**: Change from GET `/search/` to POST `/api/repository/submit`

**Rationale**:
- GET requests should be idempotent; triggering processing is not
- POST allows structured JSON body for complex options
- Cleaner separation between page navigation and API actions

**Alternatives considered**:
- Keep GET with query params: Violates REST, limited extensibility
- Use PUT: Semantically incorrect for creation

### D2: Progress Event Structure

**Decision**: Use typed progress events with consistent schema

```python
class ProgressEvent:
    type: str  # 'step_start', 'step_progress', 'step_complete', 'file_processed', 'error'
    step: str  # 'fetch_details', 'fetch_tree', 'filter', 'insert_folders', 'summarize_files', 'summarize_folders'
    current: Optional[str]  # Current file/folder being processed
    total: Optional[int]  # Total items in current step
    completed: Optional[int]  # Completed items in current step
    message: str  # Human-readable status
    timestamp: str  # ISO8601
```

**Rationale**:
- Typed events allow frontend to render appropriate UI
- Include both machine-readable counts and human message
- Timestamp enables elapsed time calculation

### D3: Checkpoint Storage

**Decision**: Store processing state in Repository.processing_state JSON field

```python
processing_state = {
    "status": "in_progress",  # 'pending', 'in_progress', 'completed', 'failed', 'paused'
    "current_step": "summarize_files",
    "steps_completed": ["fetch_details", "fetch_tree", "filter", "insert_folders"],
    "file_progress": {
        "total": 150,
        "completed": 75,
        "failed": 2,
        "completed_paths": ["src/main.py", "src/utils.py", ...],
        "failed_paths": ["src/large_file.bin"]
    },
    "folder_progress": {
        "total": 20,
        "completed": 5,
        "completed_paths": ["src/utils", "src/models"]
    },
    "error": null,
    "started_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:05:00Z"
}
```

**Rationale**:
- JSON field is flexible for evolving schema
- Stores enough info to resume from any point
- Keeps historical paths for debugging

**Alternatives considered**:
- Separate ProcessingCheckpoint table: Over-engineered for single-job tracking
- Redis-only storage: Lost on restart, no persistence

### D4: Resume Detection Logic

**Decision**: Auto-detect incomplete processing on re-submission

```python
def should_resume(repository, force_restart=False):
    if force_restart:
        return False
    if not repository.processing_state:
        return False
    state = repository.processing_state
    if state.get('status') in ['completed', 'pending']:
        return False
    if state.get('status') in ['in_progress', 'failed', 'paused']:
        return True
    return False
```

**Rationale**:
- Default to resuming incomplete work
- Allow explicit force_restart for debugging
- Treat 'failed' as resumable (retry from checkpoint)

### D5: Logging Strategy

**Decision**: Use structured logging with loguru, add correlation ID

```python
from loguru import logger
import uuid

class ProcessingContext:
    def __init__(self, owner: str, repo: str):
        self.correlation_id = str(uuid.uuid4())[:8]
        self.owner = owner
        self.repo = repo

    def log(self, level: str, message: str, **kwargs):
        logger.bind(
            correlation_id=self.correlation_id,
            owner=self.owner,
            repo=self.repo,
            **kwargs
        ).log(level, message)
```

Log format: `[{time}] [{level}] [{correlation_id}] {owner}/{repo} - {message}`

**Rationale**:
- Correlation ID links all logs for one processing job
- Structured binding allows filtering and aggregation
- Already using loguru, minimal change

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Processing state grows large for huge repos | Limit completed_paths to last N entries, store count only |
| JSON field not queryable | Add indexed `processing_status` enum field for queries |
| Resume may miss code changes | Compare commit SHA, force restart if different |
| SSE connection drops | Frontend reconnects automatically, state persisted |

## Migration Plan

### Phase 1: Add new endpoint (backward compatible)
1. Add POST `/api/repository/submit` endpoint
2. Add `processing_state` field to Repository
3. Keep existing GET `/search/` working (deprecated)

### Phase 2: Update frontend
4. Update index.html form to use POST
5. Update processing.html with enhanced progress display
6. Add SSE reconnection logic

### Phase 3: Implement resume
7. Add checkpoint saving in services.py
8. Add resume detection and logic
9. Test resume across all processing steps

### Phase 4: Deprecate old endpoint
10. Add deprecation warning to GET `/search/`
11. Remove in future release

### Rollback
- Database migration is additive (new field), no data loss
- Old endpoint remains functional during transition
- Can disable new features via feature flag if needed

## Open Questions

1. **Checkpoint granularity**: Should we checkpoint after every file, or batch (e.g., every 10 files)?
   - Proposed: Every 10 files or 30 seconds, whichever comes first

2. **Progress streaming protocol**: Standard SSE or use Django Channels?
   - Proposed: Standard SSE with StreamingHttpResponse (already in use)

3. **Handling concurrent submissions**: Should re-submission while processing is in-progress queue, cancel, or error?
   - Proposed: Return current progress if processing, don't queue duplicate
