# progress-tracking Specification

## ADDED Requirements

### Requirement: Real-time Progress Streaming
The application MUST stream granular progress events to clients during repository processing.

#### Scenario: Progress Event Structure
- **GIVEN** a repository is being processed
- **WHEN** a client connects to the status SSE endpoint
- **THEN** the system SHALL stream events with structure: type, step, current, total, completed, message, timestamp

#### Scenario: Step Start Event
- **GIVEN** processing enters a new step (e.g., "fetch_tree", "summarize_files")
- **WHEN** the step begins
- **THEN** the system SHALL emit a `step_start` event with step name and total items (if known)

#### Scenario: Step Progress Event
- **GIVEN** processing is iterating through items in a step
- **WHEN** an item is completed
- **THEN** the system SHALL emit a `step_progress` event with completed count and current item name

#### Scenario: Step Complete Event
- **GIVEN** a processing step finishes
- **WHEN** all items in the step are processed
- **THEN** the system SHALL emit a `step_complete` event with final counts and duration

#### Scenario: File Processing Progress
- **GIVEN** the "summarize_files" step is in progress
- **WHEN** each file is summarized
- **THEN** the system SHALL emit a `file_processed` event with file path and success/failure status

#### Scenario: Error Event
- **GIVEN** an error occurs during processing
- **WHEN** the error is caught
- **THEN** the system SHALL emit an `error` event with error message and current step

### Requirement: Processing Step Visibility
The application MUST track and expose the current processing step to users.

#### Scenario: Display Current Step
- **GIVEN** a user is viewing the processing page
- **WHEN** the processing step changes
- **THEN** the UI SHALL update to show the current step name (e.g., "Fetching repository tree...")

#### Scenario: Display Progress Percentage
- **GIVEN** a step has a known total item count
- **WHEN** items are processed
- **THEN** the UI SHALL display a progress percentage (completed/total * 100)

#### Scenario: Display Current Item
- **GIVEN** a file or folder is being processed
- **WHEN** processing begins on the item
- **THEN** the UI SHALL display the current file/folder name

#### Scenario: Display Elapsed Time
- **GIVEN** processing has started
- **WHEN** the user views the processing page
- **THEN** the UI SHALL display elapsed time since processing started

### Requirement: SSE Connection Resilience
The application MUST handle SSE connection drops gracefully.

#### Scenario: Auto-reconnect on Disconnect
- **GIVEN** the SSE connection is lost
- **WHEN** the connection drops
- **THEN** the client SHALL automatically attempt to reconnect after 3 seconds

#### Scenario: Resume Progress Display After Reconnect
- **GIVEN** the SSE connection is re-established
- **WHEN** the first event is received
- **THEN** the UI SHALL update to show current progress state
