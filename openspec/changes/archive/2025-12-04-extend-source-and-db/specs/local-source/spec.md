# Local Repository Source

## ADDED Requirements

### Requirement: Support Local Directory as Repository Source
The application MUST support reading repository content (files and folders) from a local directory path specified in the configuration.

#### Scenario: Configure Local Source
Given the application is configured with `REPO_SOURCE_TYPE=local` and `LOCAL_REPO_PATH=/path/to/project`
When the repository processing task is triggered
Then the application should read files from `/path/to/project` instead of fetching from GitHub.

#### Scenario: Ignore Hidden Files
Given a local repository with `.git`, `.idea`, or `__pycache__` directories
When the repository is processed
Then these directories should be excluded from the file tree, similar to how `.gitignore` works.

#### Scenario: Local Repo Metadata
Given a local repository
When the repository details are fetched
Then the application should generate synthetic metadata (e.g., Owner="local", Repo="[Directory Name]", Default Branch="local") since GitHub API metadata is not available.
