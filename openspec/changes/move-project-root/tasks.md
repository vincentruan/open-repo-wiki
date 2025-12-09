# Tasks: Move Project Management to Root Directory

## 1. Core Structure Migration

- [x] 1.1 Move `src/manage.py` to root `manage.py` and update DJANGO_SETTINGS_MODULE to `src.core_config.settings`
- [x] 1.2 Move `src/requirements.txt` to root `requirements.txt`
- [x] 1.3 Ensure `src/__init__.py` exists for package imports
- [x] 1.4 Update `src/core_config/settings.py` BASE_DIR to point to project root (parent.parent.parent)
- [x] 1.5 Update `src/core_config/settings.py` to read `.env` from project root

## 2. Django Configuration Updates

- [x] 2.1 Update `src/core_config/wsgi.py` DJANGO_SETTINGS_MODULE to `src.core_config.settings`
- [x] 2.2 Update `src/core_config/asgi.py` DJANGO_SETTINGS_MODULE to `src.core_config.settings`
- [x] 2.3 Update `src/core_config/celery.py` DJANGO_SETTINGS_MODULE to `src.core_config.settings`
- [x] 2.4 Update templates directory path in settings.py to `BASE_DIR / 'src' / 'templates'`
- [x] 2.5 Update ROOT_URLCONF, WSGI_APPLICATION, ASGI_APPLICATION paths
- [x] 2.6 Update INSTALLED_APPS to use `src.wiki_app`
- [x] 2.7 Update urls.py to use `src.wiki_app.urls`
- [x] 2.8 Update wiki_app/apps.py name to `src.wiki_app`

## 3. Docker Configuration Updates

- [x] 3.1 Move `src/Dockerfile` to root `Dockerfile` and update COPY/WORKDIR paths
- [x] 3.2 Update `docker-compose.yml`:
  - Change `build: ./src` to `build: .`
  - Update `develop.watch` paths from `./src` to `.` and target from `/app` to `/app/src`
  - Update `command` paths for manage.py and celery
- [x] 3.3 Update `docker-compose.prod.yml`:
  - Change `context: ./src` to `context: .`
  - Update `command` paths for manage.py and celery

## 4. Internal Import Updates

- [x] 4.1 Update all absolute imports in `src/wiki_app/` to use `src.` prefix
- [x] 4.2 Update all absolute imports in `src/agent/` to use `src.` prefix
- [x] 4.3 Update all absolute imports in `src/llm/` to use `src.` prefix
- [x] 4.4 Update all absolute imports in `src/github/` to use `src.` prefix
- [x] 4.5 Update all absolute imports in `src/db/` to use `src.` prefix
- [x] 4.6 Update all test files to use correct import paths

## 5. Documentation Updates

- [x] 5.1 Update `.env.local.example` header comment (copy to root `.env` instead of `src/.env`)
- [x] 5.2 Update `CLAUDE.md` development commands:
  - Remove `cd src` requirement
  - Update venv location to root `.venv`
  - Update `.env` copy command
- [x] 5.3 Update `GEMINI.md` with new development instructions

## 6. Cleanup

- [x] 6.1 Delete old `src/manage.py`
- [x] 6.2 Delete old `src/requirements.txt`
- [x] 6.3 Delete old `src/Dockerfile`

## 7. Verification

- [x] 7.1 Test `python manage.py check` passes
- [ ] 7.2 Test Docker development workflow (docker compose up)
- [ ] 7.3 Verify Celery worker starts correctly in Docker
- [ ] 7.4 Run existing tests to ensure no regressions
