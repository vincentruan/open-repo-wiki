# multi-source-input Specification

## Purpose
TBD - created by archiving change add-multi-source-ui. Update Purpose after archive.
## Requirements
### Requirement: Support Multiple Repository Source Types
The application MUST support scanning repositories from multiple sources through the web UI, including GitHub, local folders, and generic Git URLs.

#### Scenario: GitHub Repository Input
- **GIVEN** the user selects "GitHub" source type
- **WHEN** the user enters "owner/repo" or a GitHub URL
- **THEN** the system should fetch and scan the repository from GitHub API.

#### Scenario: Local Folder Input
- **GIVEN** the user selects "Local Folder" source type
- **WHEN** the user enters an absolute file path (e.g., "/home/user/project")
- **THEN** the system should scan the local directory for wiki generation.

#### Scenario: Generic Git URL Input
- **GIVEN** the user selects "Git URL" source type
- **WHEN** the user enters a Git-compatible URL (e.g., GitLab, Bitbucket)
- **THEN** the system should clone the repository and scan it for wiki generation.

### Requirement: Source Type Auto-Detection
The application MUST auto-detect the source type from user input when possible.

#### Scenario: Auto-detect GitHub from URL
- **GIVEN** the user enters "https://github.com/owner/repo"
- **WHEN** no explicit source type is selected
- **THEN** the system should auto-detect this as a GitHub source.

#### Scenario: Auto-detect Local Path
- **GIVEN** the user enters a path starting with "/" or "~"
- **WHEN** no explicit source type is selected
- **THEN** the system should auto-detect this as a local folder source.

### Requirement: Git Repository Clone Support
The application MUST support cloning and scanning repositories from any Git-compatible URL.

#### Scenario: Clone GitLab Repository
- **GIVEN** the user enters "https://gitlab.com/owner/repo"
- **WHEN** the processing task runs
- **THEN** the system should clone the repository to a temp directory, scan it, and clean up.

#### Scenario: Clone Private Repository with Credentials
- **GIVEN** the user enters a Git URL with embedded credentials
- **WHEN** the processing task runs
- **THEN** the system should clone using the provided credentials.

