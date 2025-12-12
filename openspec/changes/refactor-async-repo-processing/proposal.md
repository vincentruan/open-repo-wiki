# Change: Refactor Async Repository Processing

## Why

The current repository submission flow uses a GET request to `/search/` which creates a Repository record and triggers processing. This has several limitations:

1. **Non-RESTful design**: Using GET for state-changing operations violates REST principles
2. **Limited progress visibility**: Current SSE only shows high-level status messages, not granular file-by-file progress
3. **No resume capability**: If processing is interrupted, the entire repository must be reprocessed from scratch
4. **Insufficient logging**: Backend logs don't provide enough detail for debugging long-running processes

## What Changes

### 1. API Refactoring
- **BREAKING**: Change repository submission from GET `/search/` to POST `/api/repository/submit`
- New endpoint accepts JSON body with `source_type`, `source_url`, and optional `options`
- Frontend form submission converted to AJAX POST

### 2. Enhanced Real-time Progress Streaming
- Upgrade from basic SSE to Streamable HTTP with structured progress events
- Progress events include: step name, current file/folder, percentage, estimated time remaining
- Granular progress for each processing phase: fetch tree, filter, insert folders, summarize files, summarize folders

### 3. Resumable Processing (Checkpoint/Resume)
- Track processing state at file and folder level in database
- Add `processing_state` field to Repository model (JSON): current step, completed files, completed folders
- On re-submission of same repository URL, detect incomplete processing and resume from last checkpoint
- New `resume` parameter in submit API to explicitly trigger resume

### 4. Enhanced Backend Logging
- Add structured logging with correlation IDs per repository processing job
- Log entry/exit for each processing step with timing
- Log individual file processing: start, success/failure, duration
- Add log level configuration per component

## Impact

- **Affected specs**:
  - `multi-source-input` (MODIFIED - submit method changes)
  - New `async-processing` capability
  - New `progress-tracking` capability
  - New `resumable-processing` capability

- **Affected code**:
  - `src/wiki_app/views.py` - New submit endpoint, modify search redirect
  - `src/wiki_app/urls.py` - Add new URL pattern
  - `src/wiki_app/services.py` - Add checkpoint saving, progress callbacks
  - `src/wiki_app/models.py` - Add processing_state field
  - `src/templates/index.html` - Convert form to POST
  - `src/templates/processing.html` - Enhanced progress display
  - `src/wiki_app/tasks.py` - Add resume logic

- **Database migration required**: Yes (add `processing_state` JSON field to Repository)

## Non-Goals

- WebSocket support (SSE/Streamable HTTP is sufficient)
- Distributed processing across multiple workers
- Real-time collaboration features
