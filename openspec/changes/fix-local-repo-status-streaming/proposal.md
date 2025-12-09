# Proposal: fix-local-repo-status-streaming

## Problem Statement

When processing a local folder repository for the first time, the frontend status page (`/api/status/<owner>/<repo>/`) hangs indefinitely even though the backend logs show "Done! Repository processed successfully."

### Root Cause Analysis

The issue stems from a **URL and owner/repo identifier mismatch** between the initial Repository record creation and the subsequent update during processing:

1. **Initial Record Creation** (`views.py:_handle_local_source`):
   - Creates Repository with `url=f"local://{path}"` (e.g., `local:///Users/foo/project`)
   - Sets `owner='local'`, `repo=f"{folder_name}_{path_hash}"` (e.g., `local/project_a1b2c3d4`)

2. **Processing Update** (`services.py:insertRepository` → `LocalRepoProvider.get_details`):
   - `LocalRepoProvider.get_details` returns `url=f"file://{self.base_path}"` (e.g., `file:///Users/foo/project`)
   - Returns `repo_owner="local"`, `repo_name=self.base_path.name` (e.g., `local/project` - **no hash**)

3. **Result**: The `aupdate_or_create` at `services.py:82` queries by URL (`file://...`), finds no match for the existing `local://...` record, and creates a **new** Repository record. The SSE endpoint polls the original record (with `local://` URL), which never gets updated to "Done" status.

### Impact

- Frontend hangs indefinitely on the processing page for local repos
- Duplicate Repository records are created in the database
- Users cannot navigate to the completed wiki

## Proposed Solution

Modify `LocalRepoProvider.get_details` to accept and return consistent URL and identifiers that match what was used during initial record creation in the view layer.

### Changes Required

1. **Extend `LocalRepoProvider.get_details`** to accept optional `expected_url`, `expected_owner`, and `expected_repo` parameters that will be used in the returned `RepoDetails`

2. **Update `tasks.py:_execute_repository_processing`** to pass the source URL information to the LocalRepoProvider so it can return consistent identifiers

3. **Ensure URL scheme consistency**: Use `local://` as the canonical scheme for local repositories (aligning with the view layer's convention)

## Alternative Approaches Considered

1. **Query by owner/repo instead of URL**: This would require changing the core `aupdate_or_create` logic in services.py, potentially affecting GitHub repos
2. **Change view layer to use `file://`**: Would break existing records and require migration
3. **Remove hash from view layer**: Would cause conflicts for same-named folders in different paths

The proposed solution is the least invasive and maintains backward compatibility.

## Scope

- **In scope**: Fixing the URL/identifier mismatch for local repositories
- **Out of scope**: Git URL repositories (requires separate investigation), general SSE improvements

## Risks

- Low risk: Changes are isolated to local repo provider path
- Need to ensure existing local repo records still work (backward compatibility)
