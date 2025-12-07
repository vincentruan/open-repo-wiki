# Tasks: Add Multi-Source UI Support

- [x] **Frontend - Source Type Selection**
    - [x] Add tab/button group for source type selection in `index.html`. <!-- id: 0 -->
    - [x] Add dynamic placeholder text based on selected source type. <!-- id: 1 -->
    - [x] Add source type as hidden form field. <!-- id: 2 -->
    - [x] Validation: Manually test UI tab switching and placeholder changes. <!-- id: 3 -->

- [x] **Backend - Source Detection**
    - [x] Create `detect_source_type()` function in `src/wiki_app/utils.py`. <!-- id: 4 -->
    - [x] Update `search()` in `views.py` to use source detection. <!-- id: 5 -->
    - [x] Validation: Test with GitHub URL, local path, GitLab URL inputs. <!-- id: 6 -->

- [x] **Backend - Local Folder Processing**
    - [x] Update `views.py` to handle local folder source type. <!-- id: 7 -->
    - [x] Update `tasks.py` to accept source_type parameter. <!-- id: 8 -->
    - [x] Update `services.py` to use LocalRepoProvider for local sources. <!-- id: 9 -->
    - [x] Validation: Scan a local folder and verify wiki generation. <!-- id: 10 -->

- [x] **Backend - Git Clone Provider**
    - [x] Create `GitRepoProvider` in `src/github/git_provider.py`. <!-- id: 11 -->
    - [x] Implement clone, scan, cleanup workflow. <!-- id: 12 -->
    - [x] Update `get_repo_provider()` to support 'git' source type. <!-- id: 13 -->
    - [x] Validation: Scan a GitLab repository and verify wiki generation. <!-- id: 14 -->

- [x] **Configuration Updates**
    - [x] Remove `REPO_SOURCE_TYPE` and `LOCAL_REPO_PATH` from `.env.example`. <!-- id: 15 -->
    - [x] Add optional `LOCAL_SCAN_BASE_PATH` for security restriction. <!-- id: 16 -->

- [x] **Documentation**
    - [x] Update `README.md` with multi-source usage instructions. <!-- id: 17 -->

