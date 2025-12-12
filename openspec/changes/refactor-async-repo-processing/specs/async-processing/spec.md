# async-processing Specification

## ADDED Requirements

### Requirement: RESTful Repository Submission API
The application MUST provide a POST endpoint for submitting repositories for processing.

#### Scenario: Submit GitHub Repository via POST
- **GIVEN** a client sends POST to `/api/repository/submit`
- **WHEN** the request body contains `{"source_type": "github", "source_url": "owner/repo"}`
- **THEN** the system SHALL create a Repository record and queue processing
- **AND** return HTTP 201 with `{"success": true, "owner": "...", "repo": "...", "status": "queued"}`

#### Scenario: Submit Local Folder via POST
- **GIVEN** a client sends POST to `/api/repository/submit`
- **WHEN** the request body contains `{"source_type": "local", "source_url": "/path/to/folder"}`
- **THEN** the system SHALL validate the path exists and queue processing
- **AND** return HTTP 201 with generated owner/repo identifiers

#### Scenario: Submit Git URL via POST
- **GIVEN** a client sends POST to `/api/repository/submit`
- **WHEN** the request body contains `{"source_type": "git", "source_url": "https://gitlab.com/owner/repo"}`
- **THEN** the system SHALL parse the URL and queue processing

#### Scenario: Invalid Source Type Rejected
- **GIVEN** a client sends POST to `/api/repository/submit`
- **WHEN** the request body contains an invalid source_type
- **THEN** the system SHALL return HTTP 400 with error message

#### Scenario: Duplicate Repository Submission
- **GIVEN** a repository is already being processed
- **WHEN** a client submits the same repository URL
- **THEN** the system SHALL return the existing processing status instead of queuing duplicate

### Requirement: Asynchronous Processing with Celery
The application MUST process repositories asynchronously when Celery is available, with synchronous fallback.

#### Scenario: Async Processing with Celery
- **GIVEN** Celery/Redis is available
- **WHEN** a repository is submitted
- **THEN** processing SHALL be queued as a Celery task
- **AND** the API response SHALL include the task_id

#### Scenario: Sync Fallback Without Celery
- **GIVEN** Celery/Redis is not available
- **WHEN** a repository is submitted
- **THEN** processing SHALL run synchronously
- **AND** the API response SHALL indicate sync mode
