## ADDED Requirements

### Requirement: Root Directory Project Management
The project MUST support running all development commands from the project root directory without requiring developers to change into the `src/` subdirectory.

#### Scenario: Run Django commands from root
- **WHEN** a developer runs `python manage.py <command>` from the project root
- **THEN** the command executes successfully using the Django configuration

#### Scenario: Environment configuration at root
- **WHEN** a developer places `.env` file at the project root directory
- **THEN** Django settings loads environment variables from this root-level `.env` file

#### Scenario: Virtual environment at root
- **WHEN** a developer creates a virtual environment at the project root (`.venv/`)
- **THEN** all project dependencies can be installed and the application runs correctly

#### Scenario: Docker build from root
- **WHEN** running `docker compose up` from the project root
- **THEN** the application builds and starts correctly using the root-level Dockerfile

### Requirement: Standard Python Project Layout
The project MUST follow standard Python project conventions for file placement.

#### Scenario: manage.py location
- **WHEN** a developer clones the repository
- **THEN** `manage.py` is located at the project root directory

#### Scenario: requirements.txt location
- **WHEN** a developer clones the repository
- **THEN** `requirements.txt` is located at the project root directory

#### Scenario: Dockerfile location
- **WHEN** a developer clones the repository
- **THEN** `Dockerfile` is located at the project root directory
