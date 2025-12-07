# Local Development

## ADDED Requirements

### Requirement: Support SQLite for Local Development
The application MUST support SQLite as a database backend for local development, configurable via `DB_ENGINE=sqlite` environment variable.

#### Scenario: Configure SQLite
Given the environment variable `DB_ENGINE` is set to `sqlite`
When the application starts
Then it should use SQLite database stored in `db.sqlite3` file.

#### Scenario: Default Remains PostgreSQL
Given the `DB_ENGINE` environment variable is not set
When the application starts
Then it should default to using PostgreSQL backend.

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
