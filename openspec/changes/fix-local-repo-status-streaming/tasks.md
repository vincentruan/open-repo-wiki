# Tasks: fix-local-repo-status-streaming

## Implementation Tasks

1. [ ] **Modify `LocalRepoProvider.__init__`** to accept optional `source_url`, `owner`, and `repo` parameters
   - Store these as instance attributes for use in `get_details`
   - Validate: If provided, use them; otherwise, fall back to current auto-generation logic

2. [ ] **Update `LocalRepoProvider.get_details`** to use provided identifiers
   - Use `self.source_url` if set, otherwise generate `local://{path}`
   - Use `self.owner` and `self.repo` if set, otherwise use current logic
   - Change default URL scheme from `file://` to `local://` for consistency

3. [ ] **Update `tasks.py:_execute_repository_processing`** to construct proper LocalRepoProvider
   - Build the source URL as `local://{source_path}` to match view layer
   - Pass `owner` and `repo` to LocalRepoProvider constructor

4. [ ] **Add test case** for local repo processing flow
   - Verify URL consistency between initial record and provider response
   - Verify SSE endpoint returns "complete" status after processing

## Verification

- [ ] Start local dev server, submit a local folder path
- [ ] Verify processing page shows progress updates
- [ ] Verify page redirects to repo detail after completion
- [ ] Check database has only one Repository record for the path
