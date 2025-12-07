# Project Context

## Purpose
OpenRepoWiki is a Django-based web application designed to automatically generate a comprehensive wiki for any public GitHub repository. The primary goal is to provide a high-level understanding of a project's structure, file purposes, and overall architecture without requiring a user to manually read through the entire codebase. It achieves this by fetching repository contents and using Large Language Models (LLMs) to summarize files and folders.

## Tech Stack
- **Backend Framework:** Django
- **Language:** Python
- **Asynchronous Tasks:** Celery
- **Database:** PostgreSQL
- **Message Broker / Cache:** Redis
- **Containerization:** Docker & Docker Compose
- **LLM Integration:** Langchain library, supporting various providers (e.g., Deepseek, Google AI, Ollama)
- **Monitoring:** Prometheus and Grafana

## Project Conventions

### Code Style
The project follows standard Python PEP 8 guidelines and Django coding conventions. It utilizes `loguru` for structured and easy-to-use logging.

### Architecture Patterns
- **Asynchronous Processing:** Long-running repository analysis jobs are handled in the background by Celery workers to prevent blocking the web server and provide a non-blocking user experience.
- **Service Layer:** The core business logic for fetching, processing, and summarizing repositories is encapsulated in the `InsertRepoService`.
- **Concurrency:** `asyncio` and `aiohttp` are used within the service layer to perform I/O-bound operations (like fetching multiple files from GitHub) concurrently, improving performance.
- **Model-View-Template (MVT):** The web interface is built using Django's standard MVT architecture.

### Testing Strategy
The project contains some manual tests for core components like the code splitter and services. An ideal testing strategy would involve expanding unit tests for services, mocking external API calls to GitHub and LLMs, and adding integration tests for the repository processing pipeline.

### Git Workflow
The project appears to use a feature-branch workflow. Commits should be clear and descriptive.

## Domain Context
- **Repository Processing:** The core task involves fetching a repo's file tree, filtering out irrelevant files (e.g., binaries, `.gitignore`), fetching the content of whitelisted files, and then passing this content to an LLM for summarization.
- **Hierarchical Summarization:** The process is hierarchical. Individual files are summarized first. Then, the summaries of files within a directory, along with the summaries of its subdirectories, are used to generate a summary for the parent directory. This bubbles up to a top-level summary for the entire repository.

## Important Constraints
- **LLM Token Limits:** The amount of code that can be sent to the LLM in a single request is limited. The application must be mindful of token limits, splitting large codebases or files into smaller chunks for processing.
- **API Rate Limiting:** The application makes calls to the GitHub API. It must respect rate limits to avoid being blocked. An API token is required for any significant use.
- **Cost:** LLM API calls can be expensive. The prompt in the README warns that processing a single repository can consume a large number of tokens, so cheaper LLM providers are recommended.

## External Dependencies
- **GitHub API:** Used to fetch repository details, file trees, and file content.
- **LLM Provider API:** An external service (e.g., Deepseek, OpenRouter, Google AI Studio) is required to provide the language model for summarization.