# resumable-processing Specification

## ADDED Requirements

### Requirement: Processing State Persistence
The application MUST persist processing state to enable resume after interruption.

#### Scenario: Save Checkpoint During File Processing
- **GIVEN** files are being summarized
- **WHEN** a batch of files (10 files or 30 seconds) is completed
- **THEN** the system SHALL save a checkpoint with completed file paths to the database

#### Scenario: Save Checkpoint During Folder Summarization
- **GIVEN** folders are being summarized
- **WHEN** a folder summarization completes
- **THEN** the system SHALL update the checkpoint with the completed folder path

#### Scenario: Persist Processing Status
- **GIVEN** a repository is being processed
- **WHEN** the processing status changes
- **THEN** the system SHALL update the `processing_status` field (pending, in_progress, completed, failed, paused)

#### Scenario: Record Processing Error
- **GIVEN** an error occurs during processing
- **WHEN** the error is caught
- **THEN** the system SHALL record the error message and current step in processing_state

### Requirement: Resume From Checkpoint
The application MUST be able to resume interrupted processing from the last checkpoint.

#### Scenario: Detect Incomplete Processing
- **GIVEN** a repository URL is submitted
- **WHEN** the repository exists with status 'in_progress' or 'failed'
- **THEN** the system SHALL detect this as a resumable job

#### Scenario: Resume File Summarization
- **GIVEN** processing was interrupted during file summarization
- **WHEN** resume is triggered
- **THEN** the system SHALL skip files listed in `completed_paths` and process only remaining files

#### Scenario: Resume Folder Summarization
- **GIVEN** processing was interrupted during folder summarization
- **WHEN** resume is triggered
- **THEN** the system SHALL skip folders listed in `completed_paths` and process only remaining folders

#### Scenario: Force Restart Option
- **GIVEN** a user wants to restart processing from scratch
- **WHEN** the submit API is called with `force_restart: true`
- **THEN** the system SHALL clear existing state and restart from beginning

#### Scenario: Commit SHA Change Detection
- **GIVEN** a repository was partially processed with a specific commit SHA
- **WHEN** the repository is resubmitted and the default branch has new commits
- **THEN** the system SHALL detect the SHA mismatch and suggest restart

### Requirement: Processing State Query
The application MUST provide the current processing state to clients.

#### Scenario: Query Processing State via API
- **GIVEN** a repository exists in the database
- **WHEN** a client requests the repository status
- **THEN** the response SHALL include the full processing_state JSON

#### Scenario: Include Resume Information
- **GIVEN** a repository has incomplete processing
- **WHEN** a client queries the status
- **THEN** the response SHALL indicate `resumable: true` and last checkpoint time

### Requirement: Enhanced Backend Logging
The application MUST provide detailed structured logging for processing jobs.

#### Scenario: Correlation ID in Logs
- **GIVEN** a repository processing job starts
- **WHEN** logs are emitted during processing
- **THEN** all logs SHALL include a unique correlation_id for the job

#### Scenario: Log File Processing Events
- **GIVEN** a file is being processed
- **WHEN** processing starts and completes
- **THEN** the system SHALL log: file path, start time, end time, success/failure, error if any

#### Scenario: Log Step Timing
- **GIVEN** a processing step completes
- **WHEN** the step finishes
- **THEN** the system SHALL log: step name, duration, items processed, success/failure count

#### Scenario: Log Processing Summary
- **GIVEN** repository processing completes (success or failure)
- **WHEN** processing ends
- **THEN** the system SHALL log: total duration, files processed, folders processed, errors count
