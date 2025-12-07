# Add Local Development Support

## Goal Description
This change enables running the OpenRepoWiki application directly in a local development environment without requiring Docker. Currently, the application requires PostgreSQL, Redis, and Celery worker to be running, which makes local development cumbersome.

## User Review Required
> [!IMPORTANT]
> **SQLite Limitations**: SQLite doesn't support some PostgreSQL-specific features. For production use or full testing, Docker remains the recommended approach.
>
> **Async Processing**: In local development mode, repository processing can run synchronously (blocking) instead of through Celery, which simplifies setup but may cause the web request to hang for large repositories.

## Proposed Changes

### Configuration
#### [MODIFY] `src/core_config/settings.py`
- Add `DB_ENGINE=sqlite` support for local development.
- When using SQLite, use a local file `db.sqlite3`.

#### [MODIFY] `.env.example`
- Add `DB_ENGINE=sqlite` option with documentation.
- Make Redis/Celery configuration optional.

### Task Processing
#### [MODIFY] `src/wiki_app/tasks.py`
- Add synchronous execution mode when Celery/Redis is not available.
- Detect if Celery broker is accessible; if not, run task synchronously.

#### [MODIFY] `src/wiki_app/views.py`
- Handle synchronous task execution gracefully in the UI.

### Documentation
#### [MODIFY] `README.md`
- Add "Local Development (No Docker)" section with step-by-step instructions.

#### [NEW] `.env.local.example`
- Template for local development without Docker (SQLite + no Celery).

## Verification Plan

### Manual Verification
1. Copy `.env.local.example` to `.env`.
2. Run `pip install -r requirements.txt`.
3. Run `python manage.py migrate`.
4. Run `python manage.py runserver`.
5. Submit a small GitHub repo and verify wiki generation works.
