# Design: Extend Source and DB Support

## Repository Fetcher Abstraction

### Problem
Currently, `InsertRepoService` directly calls `fetch_github_repo_details`, `fetch_github_repo_tree`, and `fetch_github_repo_file`. These functions are specific to the GitHub API. To support local folders, we need to decouple the service from the GitHub implementation.

### Solution
Introduce a `RepoProvider` abstraction (protocol or abstract base class) with the following methods:

```python
class RepoProvider(Protocol):
    async def get_details(self, owner: str, repo: str) -> RepoDetails: ...
    async def get_tree(self, owner: str, repo: str, commit_sha: str) -> RepoTreeResult: ...
    async def get_file_content(self, owner: str, repo: str, sha: str, path: str) -> str: ...
```

We will implement two concrete providers:
1.  `GitHubRepoProvider`: Wraps the existing `fetch_github_*` functions.
2.  `LocalRepoProvider`: Implements file system access.

### Local Repository Mapping
For local repositories, the concepts of `owner`, `repo`, and `sha` need mapping:
-   **Owner**: Defaults to "local" or the current system user.
-   **Repo**: The name of the root directory.
-   **SHA**: Can be a hash of the current timestamp or a git commit hash if the local folder is a git repo (optional enhancement). For MVP, we can use a timestamp-based ID or "latest".

### Factory Pattern
A `RepoProviderFactory` will be responsible for returning the correct provider instance based on the `REPO_SOURCE_TYPE` environment variable.

```python
def get_repo_provider() -> RepoProvider:
    source_type = os.getenv("REPO_SOURCE_TYPE", "github")
    if source_type == "local":
        return LocalRepoProvider(base_path=os.getenv("LOCAL_REPO_PATH"))
    return GitHubRepoProvider()
```

## Database Configuration

### Problem
`settings.py` hardcodes the PostgreSQL engine.

### Solution
Update `settings.py` to read `DB_ENGINE` from `.env`.

```python
DB_ENGINE = env('DB_ENGINE', default='postgres')

if DB_ENGINE == 'mysql':
    db_engine = 'django.db.backends.mysql'
    db_port = env('DB_PORT', default='3306')
else:
    db_engine = 'django.db.backends.postgresql'
    db_port = env('DB_PORT', default='5432')

DATABASES = {
    'default': {
        'ENGINE': db_engine,
        # ... other params
    }
}
```

## Impact on Existing Logic
-   `InsertRepoService` will need to be updated to use `self.repo_provider` instead of direct imports.
-   `views.py` might need adjustment if we want to support triggering the local repo processing via the UI (e.g., a "Process Local Repo" button if configured).
