# Change: Move Project Management to Root Directory

## Why
The current project structure requires developers to work from the `src/` directory, which creates friction and inconsistency with standard Python/Django project conventions. Having `.env`, `manage.py`, and other management files in the root directory improves developer experience and simplifies both local development and Docker workflows.

## What Changes
- Move `.env` file location from `src/.env` to project root `.env`
- Move `manage.py` from `src/manage.py` to root `manage.py`
- Move `requirements.txt` from `src/requirements.txt` to root `requirements.txt`
- Reorganize `src/` to become a Python package containing only application code
- Update Django settings to read `.env` from project root
- Update Dockerfile and docker-compose.yml to reflect new structure
- Update CLAUDE.md with new development commands

## Impact
- Affected specs: `local-development`
- Affected code:
  - `src/core_config/settings.py` - BASE_DIR and .env path
  - `src/manage.py` → `manage.py` (move and update)
  - `src/Dockerfile` → `Dockerfile` (move and update)
  - `docker-compose.yml` - build context and paths
  - `docker-compose.prod.yml` - build context and paths
  - `.env.local.example` - update copy instructions
  - `CLAUDE.md` - update development commands
  - `src/core_config/wsgi.py`, `asgi.py`, `celery.py` - module paths
