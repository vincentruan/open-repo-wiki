# Design: Multi-Source UI Support

## Current Architecture
```
User Input (GitHub URL/owner/repo)
       ↓
   views.py (search)
       ↓
   tasks.py (process_repository_task)
       ↓
   services.py (InsertRepoService)
       ↓
   provider.py (GitHubRepoProvider)
       ↓
   GitHub API
```

## Proposed Architecture
```
User Input (with source type selection)
       ↓
   views.py (search) - detect source type
       ↓
   tasks.py (process_repository_task) - with source_type param
       ↓
   services.py (InsertRepoService) - with configured provider
       ↓
   provider.py (get_repo_provider with source_type)
       ↓
   ┌─────────────────────────────────────────────────┐
   │ GitHubRepoProvider │ LocalRepoProvider │ GitRepoProvider │
   └─────────────────────────────────────────────────┘
```

## Source Type Detection

### Input Patterns
| Input Pattern | Source Type | Example |
|--------------|-------------|---------|
| `owner/repo` | GitHub | `daeisbae/open-repo-wiki` |
| `github.com/...` | GitHub | `https://github.com/owner/repo` |
| `/path/...` or `~/...` | Local | `/home/user/project` |
| `C:\...` or `D:\...` | Local (Windows) | `C:\Projects\myapp` |
| `gitlab.com/...` | Git Clone | `https://gitlab.com/owner/repo` |
| `bitbucket.org/...` | Git Clone | `https://bitbucket.org/owner/repo` |
| `*.git` URL | Git Clone | `git@github.com:owner/repo.git` |

### Detection Logic
```python
def detect_source_type(query: str) -> tuple[str, dict]:
    """
    Detect source type from user input.
    Returns (source_type, parsed_info)
    """
    if query.startswith('/') or query.startswith('~') or re.match(r'^[A-Z]:\\', query):
        return 'local', {'path': query}
    
    if 'github.com' in query:
        owner, repo = parse_github_url(query)
        return 'github', {'owner': owner, 'repo': repo}
    
    if any(host in query for host in ['gitlab.com', 'bitbucket.org', '.git']):
        return 'git', {'url': query}
    
    # Default: assume owner/repo format for GitHub
    if '/' in query and not query.startswith('http'):
        parts = query.split('/')
        return 'github', {'owner': parts[0], 'repo': parts[1]}
    
    return 'unknown', {}
```

## Git Clone Provider

For non-GitHub Git repositories, we clone to a temporary directory:

```python
class GitRepoProvider:
    def __init__(self, git_url: str):
        self.git_url = git_url
        self.temp_dir = None
        self.local_provider = None
    
    async def clone(self):
        """Clone repository to temp directory."""
        self.temp_dir = tempfile.mkdtemp(prefix='openrepowiki_')
        subprocess.run(['git', 'clone', '--depth', '1', self.git_url, self.temp_dir])
        self.local_provider = LocalRepoProvider(self.temp_dir)
    
    async def cleanup(self):
        """Remove temp directory after processing."""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
```

## UI Design

### Tab-based Source Selection
```
┌─────────────────────────────────────────────────────────────┐
│  [GitHub]  [Local Folder]  [Git URL]                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Enter GitHub repository (e.g., owner/repo)      [→] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Input Placeholders by Source
- **GitHub**: "Enter GitHub repository (e.g., owner/repo)"
- **Local Folder**: "Enter absolute path (e.g., /home/user/project)"
- **Git URL**: "Enter Git repository URL (e.g., https://gitlab.com/owner/repo)"

## Security Considerations

### Local Path Restrictions
- Validate paths are absolute
- (Optional) Restrict to configured base directory
- Check file existence and read permissions
- Exclude sensitive directories (e.g., `/etc`, `/root`)

### Git Clone Safety
- Use `--depth 1` to minimize clone size
- Set timeout for clone operations
- Clean up temp directories after processing
- Validate URL format before cloning
