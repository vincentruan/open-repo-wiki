# Tasks: Refactor Async Repository Processing

## 1. Database Schema Changes
- [x] 1.1 Add `processing_state` JSONField to Repository model
- [x] 1.2 Add `processing_status` CharField (enum: pending, in_progress, completed, failed, paused) for indexed queries
- [x] 1.3 Create and apply database migration
- [x] 1.4 Verify migration with `python manage.py check`

## 2. API Endpoint Implementation
- [x] 2.1 Create new POST `/api/repository/submit` endpoint in views.py
- [x] 2.2 Implement request validation for source_type and source_url
- [x] 2.3 Add URL pattern to urls.py
- [x] 2.4 Keep RepositoryQueueView.post for backward compatibility
- [x] 2.5 Keep GET `/search/` for backward compatibility

## 3. Progress Event System
- [x] 3.1 Create ProgressEvent dataclass in new `progress.py` module
- [x] 3.2 Create ProgressTracker class with event emission callbacks
- [x] 3.3 Modify InsertRepoService to accept ProgressTracker
- [x] 3.4 Add progress events at each processing step
- [x] 3.5 Update SSE endpoint to stream progress info as JSON

## 4. Checkpoint/Resume Implementation
- [x] 4.1 Create CheckpointManager class for state persistence
- [x] 4.2 Add checkpoint saving after each batch of files (every 10 files)
- [x] 4.3 Add checkpoint saving after each folder summarization
- [x] 4.4 Implement `should_resume()` detection logic
- [x] 4.5 Implement resume logic in InsertRepoService
- [x] 4.6 Skip already-completed files/folders during resume
- [x] 4.7 Add `force_restart` parameter to submit API

## 5. Enhanced Logging
- [x] 5.1 Create ProcessingContext class with correlation ID
- [x] 5.2 Add structured logging to InsertRepoService
- [x] 5.3 Log file processing: start, success/failure, duration
- [x] 5.4 Log folder summarization: start, complete, child count
- [x] 5.5 Add timing summaries at step completion

## 6. Frontend Updates
- [x] 6.1 Update index.html form to POST JSON to `/api/repository/submit`
- [x] 6.2 Handle API response and redirect to processing page
- [x] 6.3 Update processing.html with progress bar percentage
- [x] 6.4 Add file/folder count display
- [x] 6.5 Add current step name display
- [x] 6.6 Add SSE reconnection on disconnect (exponential backoff)
- [x] 6.7 Show "Resuming from checkpoint" message when applicable

## 7. Testing & Validation
- [x] 7.1 Verify Django syntax and checks pass
- [ ] 7.2 Test POST submission for GitHub repository
- [ ] 7.3 Test POST submission for local folder
- [ ] 7.4 Test POST submission for Git URL
- [ ] 7.5 Test resume after manual interruption
- [ ] 7.6 Test progress display updates in real-time
- [ ] 7.7 Test backward compatibility with existing repositories

## 8. Documentation
- [ ] 8.1 Update CLAUDE.md with new API endpoint
- [ ] 8.2 Add inline code comments for ProgressTracker and CheckpointManager

## Dependencies

- Task 2 depends on Task 1 (need model fields) ✓
- Task 3 depends on Task 1 (need progress state storage) ✓
- Task 4 depends on Task 1 and 3 (need checkpoint storage and progress tracking) ✓
- Task 5 can run in parallel with Tasks 2-4 ✓
- Task 6 depends on Tasks 2 and 3 (need API and progress events) ✓
- Task 7 depends on all implementation tasks
- Task 8 depends on Task 7

## Parallelizable Work

- Tasks 1, 5 can start immediately in parallel ✓
- Tasks 2, 3, 4 can run in parallel after Task 1 ✓
- Task 6 can start once Task 2 API is ready (partial) ✓
