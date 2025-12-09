# Design: Move Project Management to Root Directory

## Context
Currently, the OpenRepoWiki project requires developers to work from the `src/` directory for local development. This creates several friction points:
- Developers must `cd src` before running any Django commands
- The `.env` file is located at `src/.env` which is non-standard
- Virtual environment is created inside `src/.venv`
- Docker build context is `./src` which complicates path references

Standard Python/Django projects place `manage.py`, `requirements.txt`, and `.env` at the project root.

## Goals / Non-Goals
**Goals:**
- Enable developers to run all commands from the project root directory
- Place `.env` at project root for conventional configuration
- Simplify Docker build context to use project root
- Maintain backward compatibility for existing deployments during transition

**Non-Goals:**
- Restructuring the internal `src/` package organization (agent/, wiki_app/, etc.)
- Changing the Django app structure
- Modifying the application logic

## Decisions

### Decision 1: Move manage.py to project root
- **What**: Place `manage.py` at project root, update DJANGO_SETTINGS_MODULE to `src.core_config.settings`
- **Why**: Enables running `python manage.py` directly from project root
- **Alternative considered**: Wrapper script in root that calls `src/manage.py` - rejected as adds indirection

### Decision 2: Keep src/ as a package
- **What**: The `src/` directory remains as the main Python package containing all application code
- **Why**: Preserves the current import structure with minimal changes to internal modules
- **Alternative considered**: Rename `src/` to `openrepowiki/` - rejected as larger scope change

### Decision 3: Update BASE_DIR to project root
- **What**: Change `settings.py` BASE_DIR from `src/` to project root
- **Why**: Aligns paths for templates, static files, and .env reading
- **Impact**: Template paths change from `BASE_DIR / 'templates'` to `BASE_DIR / 'src' / 'templates'`

### Decision 4: Root-level Dockerfile
- **What**: Move Dockerfile to project root with adjusted COPY paths
- **Why**: Simplifies docker-compose configuration with build context at root
- **Impact**: Container structure remains same, only build paths change

## Directory Structure (After)

```
project-root/
├── .env                          # Configuration (moved from src/)
├── manage.py                     # Django CLI (moved from src/)
├── requirements.txt              # Dependencies (moved from src/)
├── Dockerfile                    # Docker build (moved from src/)
├── docker-compose.yml            # Updated paths
├── CLAUDE.md                     # Updated commands
├── src/                          # Python package (unchanged internally)
│   ├── __init__.py
│   ├── core_config/              # Django settings
│   │   ├── settings.py           # Updated BASE_DIR
│   │   ├── wsgi.py               # Updated module path
│   │   ├── asgi.py               # Updated module path
│   │   └── celery.py             # Updated module path
│   ├── agent/
│   ├── wiki_app/
│   ├── github/
│   ├── llm/
│   ├── db/
│   └── templates/
└── openspec/
```

## Risks / Trade-offs

### Risk 1: Import path changes
- **Risk**: Existing imports like `from core_config import settings` may break
- **Mitigation**: All internal imports already use relative or full paths; verify with tests
- **Likelihood**: Low - internal imports are within `src/` package

### Risk 2: Docker volume mount changes
- **Risk**: Development watch/sync paths in docker-compose need updating
- **Mitigation**: Test docker compose up before merging
- **Likelihood**: Medium - paths need careful updating

### Risk 3: CI/CD pipeline impact
- **Risk**: GitHub Actions deployment may reference old paths
- **Mitigation**: Review `.github/workflows/deploy.yml` and update as needed

## Migration Plan

1. Create new files at root level (manage.py, requirements.txt, Dockerfile)
2. Update all configuration to use new paths
3. Test both local and Docker workflows
4. Remove old files from src/ (manage.py, requirements.txt, Dockerfile)
5. Update documentation

**Rollback**: Git revert if issues discovered; no data migration required.

## Open Questions
- None - approach is straightforward file reorganization
