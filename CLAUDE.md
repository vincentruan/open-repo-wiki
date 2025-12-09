# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenRepoWiki automatically generates wiki documentation for GitHub repositories by using LLMs to summarize code files and folder structures. It supports multiple repository sources (GitHub, local folders, Git URLs) and uses a hierarchical bottom-up summarization approach.

## Development Commands

```bash
# Local development (from project root)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.local.example .env  # Configure DB and LLM settings
python manage.py migrate
python manage.py runserver

# Docker development
docker compose up  # or docker compose up -d

# Run Celery worker (for async processing)
celery -A src.core_config worker -l info

# Database migrations
python manage.py makemigrations src.wiki_app
python manage.py migrate
python manage.py check_tables  # Validate table structures
```

## Architecture

### Processing Pipeline (wiki_app/services.py)
The `InsertRepoService` orchestrates the entire summarization workflow:
1. Fetch repository metadata via `RepoProvider`
2. Filter file tree (whitelist/blacklist in `github/filterfile.py`)
3. Insert folder structure into database
4. Parallel processing: fetch files + summarize folders concurrently using asyncio
5. Bottom-up summarization: files → folders → root (branch-level summary)

### Key Components

**Agent Layer** (`src/agent/`):
- `CodeProcessor`: Summarizes individual code files using LLM with code splitting
- `FolderProcessor`: Aggregates file/subfolder summaries into folder summaries
- `DependencyParser`: Extracts import statements to build dependency graphs
- Schema enforcement via Pydantic (`FileSchema`, `FolderSchema`)

**Repository Providers** (`src/github/`):
- `RepoProvider` protocol with `GitHubRepoProvider` and `LocalRepoProvider` implementations
- Set `REPO_SOURCE_TYPE=local` + `LOCAL_REPO_PATH` for local folder scanning
- File filtering: `filterfile.py` contains whitelist/blacklist for file extensions

**LLM Integration** (`src/llm/`):
- Factory pattern: `LLMFactory.create_provider()` based on `LLM_PROVIDER` env var
- Supported: `deepseek`, `openrouter`
- Token limits configured via `TOKEN_PROCESSING_CHARACTER_LIMIT` (default 30000)

**Database Models** (`src/wiki_app/models.py`):
- Hierarchy: Repository → Branch → Folder → File
- Folders store `dependency_graph` (Mermaid diagrams)
- Files store `dependencies` (JSON array of imports)

### Django + Celery Structure

- Django app: `wiki_app` with REST API and SSE status streaming
- Celery for async processing in production (Redis broker)
- Local dev runs synchronously without Celery

## OpenSpec Integration

This project uses OpenSpec for spec-driven development. When working on changes involving:
- New capabilities or breaking changes
- Architecture shifts or performance work
- Ambiguous requirements

Refer to `openspec/AGENTS.md` for proposal workflow and spec format.

## Environment Variables

Required:
- `GITHUB_TOKEN`: GitHub API access
- `LLM_PROVIDER`: `deepseek` or `openrouter`
- `LLM_APIKEY`: API key for LLM provider
- `LLM_MODELNAME`: Model identifier (e.g., `deepseek-chat`)

Database (PostgreSQL default, MySQL supported):
- `DB_ENGINE`: `postgresql` (default) or `mysql`
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

Processing limits:
- `TOKEN_PROCESSING_CHARACTER_LIMIT`: Max chars per LLM request (default 30000)
- `MAX_FILES_ALLOWED`: Skip repos with >600 files
