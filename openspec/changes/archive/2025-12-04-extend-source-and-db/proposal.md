# Extend Source and DB Support

## Goal Description
This change extends the OpenRepoWiki application to support two new capabilities:
1.  **Local Repository Source**: Allow generating a wiki from a local directory path instead of only GitHub URLs. This enables users to document private or local projects without pushing them to GitHub.
2.  **MySQL Database Support**: Add support for MySQL as a database backend, configurable via environment variables, providing more flexibility in deployment environments.

## User Review Required
> [!IMPORTANT]
> **Local Source Configuration**: The local source mode will be configured via `.env` variables (`REPO_SOURCE_TYPE=local` and `LOCAL_REPO_PATH`). When enabled, the application's behavior regarding the "input" (owner/repo) needs to be defined. The proposal assumes that in "local" mode, the application will either:
> 1.  Automatically process the configured local path as a single "repo".
> 2.  Or allow the user to trigger processing for this specific local path.
>
> **Database Driver**: `mysqlclient` (or `pymysql`) will be added to `requirements.txt`. Users switching to MySQL will need to ensure they have the necessary system libraries installed (e.g., `default-libmysqlclient-dev` on Ubuntu) or use a Docker image that includes them.

## Proposed Changes

### Configuration
#### [MODIFY] `.env.example`
- Add `DB_ENGINE` (postgres/mysql).
- Add `REPO_SOURCE_TYPE` (github/local).
- Add `LOCAL_REPO_PATH`.

### Core Config
#### [MODIFY] `src/core_config/settings.py`
- Update `DATABASES` setting to dynamically configure the engine based on `DB_ENGINE`.

### Wiki App
#### [MODIFY] `src/wiki_app/services.py`
- Refactor `InsertRepoService` to abstract the repository fetching logic.
- Implement logic to choose between GitHub and Local fetchers.

#### [NEW] `src/github/fetch_local.py`
- Implement local file system traversal to match the `RepoTreeResult` structure.

### Documentation
#### [MODIFY] `README.md`
- Update documentation to explain how to configure local source and MySQL.

## Verification Plan

### Automated Tests
- Add unit tests for `fetch_local.py` to ensure it correctly traverses directories and respects ignore rules.
- Test DB configuration switching (mocking env vars).

### Manual Verification
- **Local Repo**: Configure `.env` to point to a local folder (e.g., the project itself). Run the processing task and verify the wiki is generated.
- **MySQL**: Spin up a MySQL container, update `.env`, run migrations, and verify the app starts and functions correctly.
