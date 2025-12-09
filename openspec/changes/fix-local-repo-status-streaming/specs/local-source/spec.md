# local-source Specification Delta

## MODIFIED Requirements

### Requirement: Support Local Directory as Repository Source

The application MUST support reading repository content (files and folders) from a local directory path specified in the configuration. **The provider MUST return consistent URL and identifier values that match the initial repository record created by the view layer.**

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

#### Scenario: Consistent Repository Identifiers
Given a local repository processing is triggered with owner="local" and repo="project_a1b2c3d4" and source URL "local:///path/to/project"
When the `LocalRepoProvider.get_details` method is called
Then it MUST return a `RepoDetails` object with:
  - `url` matching the source URL passed during initialization ("local:///path/to/project")
  - `repo_owner` matching the owner passed during initialization ("local")
  - `repo_name` matching the repo passed during initialization ("project_a1b2c3d4")
So that the `aupdate_or_create` in services.py finds and updates the existing repository record.

#### Scenario: SSE Status Updates for Local Repos
Given a local repository is being processed
When the user views the processing status page at `/api/status/local/project_a1b2c3d4/`
Then the SSE endpoint should return status updates as processing progresses
And when processing completes with "Done! Repository processed successfully."
Then the SSE endpoint should return `{"status": "complete"}` within 2 seconds
And the user should be redirected to the repository detail page.
