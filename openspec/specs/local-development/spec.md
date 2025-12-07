# local-development Specification

## Purpose
Support for running the application locally without Docker for development purposes.

## Requirements
### Requirement: Synchronous Task Execution Fallback
The application MUST support running repository processing tasks synchronously when Celery/Redis is not available.

#### Scenario: No Redis Available
Given Redis is not running
When a repository processing request is made
Then the task should execute synchronously in the web process.

#### Scenario: Redis Available
Given Redis and Celery worker are running
When a repository processing request is made
Then the task should be queued for async processing as normal.


