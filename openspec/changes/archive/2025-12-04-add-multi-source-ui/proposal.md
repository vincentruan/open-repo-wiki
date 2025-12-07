# Add Multi-Source UI Support

## Goal Description
This change extends the web UI to support multiple repository sources directly through user input, replacing the current .env-based configuration approach. Users can now scan:
1. **GitHub repositories** (current behavior)
2. **Local folders** (absolute path on server)
3. **Other Git hosts** (GitLab, Bitbucket, self-hosted Git)

## User Review Required
> [!IMPORTANT]
> **Local Folder Security**: Allowing users to input local paths poses security risks. Consider:
> 1. Restricting local path input to admin users only
> 2. Whitelisting allowed base directories via configuration
> 3. Sandboxing the local path to a specific directory
>
> **Git Clone for Non-GitHub**: For GitLab/Bitbucket support, we need to either:
> 1. Clone the repository to a temporary directory, then scan (simpler, more universal)
> 2. Implement provider-specific APIs (complex, but doesn't require git clone)
>
> Please advise on preferred approach for security and non-GitHub support.

## Proposed Changes

### Frontend
#### [MODIFY] `src/templates/index.html`
- Add source type selector (tabs or dropdown): GitHub, Local Folder, Git URL
- Adjust input placeholder and validation based on selected source type
- For local folders: show file path input
- For Git URL: allow any git-compatible URL (GitLab, Bitbucket, etc.)

### Backend - Views
#### [MODIFY] `src/wiki_app/views.py`
- Extend `search()` function to detect source type from input
- Handle local folder paths (validate existence, permissions)
- Handle generic Git URLs (clone to temp, use LocalRepoProvider)

### Backend - Services
#### [MODIFY] `src/wiki_app/services.py`
- Accept source type parameter
- Route to appropriate provider based on source type

### Backend - Tasks
#### [MODIFY] `src/wiki_app/tasks.py`
- Add source_type and source_path parameters
- Support cloning Git repos to temp directory for non-GitHub sources

#### [NEW] `src/github/git_provider.py`
- Generic Git provider that clones any Git URL to temp directory
- Wraps LocalRepoProvider after cloning

### Configuration
#### [MODIFY] `.env.example`
- Remove `REPO_SOURCE_TYPE` and `LOCAL_REPO_PATH` (now UI-driven)
- Add `LOCAL_SCAN_BASE_PATH` for security (restrict local scans to this dir)

## Verification Plan

### Manual Verification
1. **GitHub source**: Enter `owner/repo` or GitHub URL → works as before
2. **Local folder**: Enter `/path/to/project` → scans local directory
3. **Git URL**: Enter `https://gitlab.com/owner/repo` → clones and scans
