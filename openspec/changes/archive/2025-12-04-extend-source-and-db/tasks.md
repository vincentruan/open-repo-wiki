# Tasks: Extend Source and DB Support

- [x] **Database Configuration**
    - [x] Update `src/core_config/settings.py` to support `DB_ENGINE` env var. <!-- id: 0 -->
    - [x] Add `mysqlclient` to `src/requirements.txt`. <!-- id: 1 -->
    - [x] Update `.env.example` with new DB and Repo config variables. <!-- id: 2 -->
    - [ ] Validation: Verify app starts with `DB_ENGINE=postgres` (default) and `DB_ENGINE=mysql` (if mysql server available). <!-- id: 3 -->

- [x] **Repository Provider Abstraction**
    - [x] Create `src/github/provider.py` defining `RepoProvider` protocol. <!-- id: 4 -->
    - [x] Implement `GitHubRepoProvider` in `src/github/provider.py` moving logic from `fetch_repo.py` or wrapping it. <!-- id: 5 -->
    - [x] Refactor `InsertRepoService` in `src/wiki_app/services.py` to accept a `RepoProvider` instead of direct calls. <!-- id: 6 -->
    - [ ] Validation: Run existing tests or manual test to ensure GitHub repo processing still works. <!-- id: 7 -->

- [x] **Local Repository Provider**
    - [x] Implement `LocalRepoProvider` in `src/github/local_provider.py`. <!-- id: 8 -->
    - [x] Implement `get_details`, `get_tree`, and `get_file_content` for local file system. <!-- id: 9 -->
    - [x] Implement filtering logic for local files (ignoring `.git`, etc.). <!-- id: 10 -->
    - [ ] Validation: Write a unit test to verify `LocalRepoProvider` correctly lists files in a dummy directory. <!-- id: 11 -->

- [x] **Integration**
    - [x] Implement `RepoProviderFactory` to choose provider based on `.env`. <!-- id: 12 -->
    - [x] Update `InsertRepoService` instantiation to use the factory. <!-- id: 13 -->
    - [ ] Validation: Configure `.env` for local repo and trigger processing. Verify wiki is generated. <!-- id: 14 -->

- [x] **Documentation**
    - [x] Update `README.md` with instructions for Local Source and MySQL setup. <!-- id: 15 -->


