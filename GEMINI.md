# OpenRepoWiki Gemini Assistant Context

## Project Overview

This project is a Django web application called "OpenRepoWiki" that automatically generates a wiki for any given GitHub repository. It uses Celery for asynchronous task processing, Redis as a message broker and cache, and PostgreSQL as the database. 

The core logic is in the `wiki_app` Django app. When a user enters a GitHub repository URL, a Celery task is triggered to process the repository. The `InsertRepoService` in `wiki_app/services.py` fetches the repository details and file tree from GitHub, filters out irrelevant files, and then uses a language model (LLM) via the `langchain` library to summarize the files and folders. The summaries are then saved to the database and displayed to the user.

The project also includes a monitoring stack with Prometheus and Grafana, which is configured in the `monitoring` directory.

## Building and Running

The project uses Docker for local development. To build and run the project:

1.  **Configure the environment:**
    *   Copy the `.env.example` file to `.env`.
    *   Edit the `.env` file to include your GitHub token and LLM provider configuration.

2.  **Start the services:**
    *   Run the following command to build and start the Docker containers:
        ```bash
        docker-compose up
        ```

This will start the Django application, a PostgreSQL database, a Redis instance, and a Celery worker. The application will be available at `http://localhost:8000`.

## Development Conventions

*   **Django:** The project follows the standard Django project structure. The main application logic is in the `wiki_app` directory.
*   **Celery:** Asynchronous tasks are defined in `wiki_app/tasks.py` and are used to process repositories in the background.
*   **Asyncio:** The `InsertRepoService` uses `asyncio` to perform I/O-bound operations (like fetching files from GitHub) concurrently.
*   **Logging:** The project uses the `loguru` library for logging.
*   **Monitoring:** The project uses `django-prometheus` to export metrics to Prometheus. A Grafana dashboard is also provided in the `monitoring` directory.
