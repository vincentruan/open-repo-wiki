# Design: fix-local-repo-status-streaming

## Current Flow (Broken)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. User submits local path "/Users/foo/project"                             │
│                                                                             │
│ 2. views.py:_handle_local_source                                            │
│    └─ Creates Repository:                                                   │
│       - url = "local:///Users/foo/project"                                  │
│       - owner = "local"                                                     │
│       - repo = "project_a1b2c3d4"                                           │
│                                                                             │
│ 3. tasks.py triggers processing                                             │
│                                                                             │
│ 4. services.py:insertRepository                                             │
│    └─ Calls LocalRepoProvider.get_details()                                 │
│       └─ Returns RepoDetails with:                                          │
│          - url = "file:///Users/foo/project"  ← MISMATCH!                   │
│          - repo_owner = "local"                                             │
│          - repo_name = "project"  ← MISMATCH (no hash)!                     │
│                                                                             │
│ 5. services.py:82 aupdate_or_create(url=file://...)                         │
│    └─ No match found → Creates NEW Repository record                        │
│                                                                             │
│ 6. SSE endpoint polls for owner="local", repo="project_a1b2c3d4"            │
│    └─ Original record never updated → Hangs forever                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Proposed Flow (Fixed)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. User submits local path "/Users/foo/project"                             │
│                                                                             │
│ 2. views.py:_handle_local_source                                            │
│    └─ Creates Repository:                                                   │
│       - url = "local:///Users/foo/project"                                  │
│       - owner = "local"                                                     │
│       - repo = "project_a1b2c3d4"                                           │
│                                                                             │
│ 3. tasks.py triggers processing with source_type='local', source_path=...  │
│    └─ Constructs LocalRepoProvider with:                                    │
│       - source_url = "local:///Users/foo/project"                           │
│       - owner = "local"                                                     │
│       - repo = "project_a1b2c3d4"                                           │
│                                                                             │
│ 4. services.py:insertRepository                                             │
│    └─ Calls LocalRepoProvider.get_details()                                 │
│       └─ Returns RepoDetails with MATCHING values:                          │
│          - url = "local:///Users/foo/project"  ← MATCHES!                   │
│          - repo_owner = "local"                                             │
│          - repo_name = "project_a1b2c3d4"  ← MATCHES!                       │
│                                                                             │
│ 5. services.py:82 aupdate_or_create(url=local://...)                        │
│    └─ Match found → Updates existing record with status                     │
│                                                                             │
│ 6. SSE endpoint polls for owner="local", repo="project_a1b2c3d4"            │
│    └─ Record updated to "Done" → Returns complete → Redirects               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Code Changes

### 1. LocalRepoProvider (src/github/local_provider.py)

```python
class LocalRepoProvider:
    def __init__(
        self,
        base_path: str,
        ignore_patterns: Optional[Set[str]] = None,
        source_url: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ):
        self.base_path = Path(base_path).resolve()
        self.ignore_patterns = ignore_patterns or DEFAULT_IGNORE_PATTERNS
        # Store provided identifiers for consistent responses
        self._source_url = source_url
        self._owner = owner
        self._repo = repo
        # ... existing validation ...

    async def get_details(self, owner: str, repo: str) -> RepoDetails:
        # Use provided identifiers if available, otherwise auto-generate
        repo_name = self._repo if self._repo else self.base_path.name
        repo_owner = self._owner if self._owner else "local"
        url = self._source_url if self._source_url else f"local://{self.base_path}"

        return RepoDetails(
            repo_owner=repo_owner,
            repo_name=repo_name,
            url=url,
            # ... rest unchanged ...
        )
```

### 2. Task Execution (src/wiki_app/tasks.py)

```python
def _execute_repository_processing(
    owner: str,
    repo: str,
    source_type: str = 'github',
    source_path: Optional[str] = None
):
    # ...
    if source_type == 'local':
        from src.github.local_provider import LocalRepoProvider
        source_url = f"local://{source_path}"
        provider = LocalRepoProvider(
            source_path,
            source_url=source_url,
            owner=owner,
            repo=repo
        )
    # ...
```

## Backward Compatibility

- Existing local repo records with `local://` URLs will continue to work
- The changes are additive; default behavior (auto-generation) is preserved when no identifiers are passed
