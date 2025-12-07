
# OpenRepoWiki

![OpenRepoWiki Example Image](https://github.com/daeisbae/open-repo-wiki/blob/v2-main/assets/openrepowiki.png)

**OpenRepoWiki** is a tool that automatically generates a comprehensive wiki page for any given GitHub repository. I **hate** reading code, but I want to learn how to build stuffs from websites to databases. That's why I built **OpenRepoWiki**, where we can understand the purpose of that files and folders of a particular repository.

## Features

- **Automated Wiki Generation:** Creates a summarized overview of a repository's purpose, functionality, and core components.
- **Codebase Analysis:** Analyzes the code structure, identifies key files and functions, and explains their roles within the project.
- **Dependency Graph:** Shows how files in each folder relate to each other using Mermaid diagrams with labeled arrows (e.g., "provides config to", "transforms data for").
- **Link To That Code Block:** The sky-blue highlighted code block will point to the Github link where it referenced.

## Installation

### Requirements

- Either Google AI Studio or Deepseek API Key
- Github API Key (To get more quota requesting the repository data)
- Amazon S3 (You can ignore the parameters if you are going to use it locally. You need to use certificate for your Database if you are going to host it.)
- Docker (If you are hosting locally)

### Configuration (Docker)

1. Copy `.env.example` to `.env`
2. Configure just `github token` and `LLM configurations`
3. Run `docker compose up` or `docker compose up -d` to hide the output

### Local Development (No Docker)

For local development without Docker, you need to connect to a MySQL or PostgreSQL database:

1. **Setup environment:**
   ```bash
   cd src
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp ../.env.local.example .env
   # Edit .env to add your database connection details and LLM_APIKEY
   ```

3. **Initialize database:**
   ```bash
   python manage.py check_tables  # Validate table structures (optional)
   python manage.py migrate
   ```

4. **Run the server:**
   ```bash
   python manage.py runserver
   ```

5. Open http://localhost:8000 in your browser.

> [!NOTE]
> In local development mode:
> - Connect to a remote MySQL or PostgreSQL database
> - Repository processing runs synchronously (may take a few minutes for large repos)
> - No Redis or Celery required



#### Ollama Configuration Guide

- It's recommended if you can run bigger LLM than 14b parameter.
- You do not need to provide the API KEY
- Set LLM_PROVIDER to Ollama (It is going to connect to default ollama endpoint)
- Set LLM_MODELNAME to the model name you can see from Ollama using the command `ollama ls`
- It is recommended to set TOKEN_PROCESSING_CHARACTER_LIMIT between 10000-20000 (Approx 300-600 lines of code) if you are using low param LLM (ex. 8b, 14b)

**Example:**

```
LLM_PROVIDER=deepseek
LLM_APIKEY=sk-....
LLM_MODELNAME=deepseek-chat
```

### Additional Information

> [!CAUTION]
> Before using this, it can easily use 1 million input / output tokens per Repository. Hence it is recommended to use cheaper LLM.

- If you are going to host it locally, you will only need to configure the Docker PostgreSQL container, Github API Key, and Google AI Studio or Deepseek API Key

### Multiple Repository Sources

OpenRepoWiki supports generating documentation from multiple sources:

#### GitHub Repositories
Enter a GitHub repository in any of these formats:
- `owner/repo` (e.g., `daeisbae/open-repo-wiki`)
- `https://github.com/owner/repo`
- `github.com/owner/repo`

#### Local Folders
Enter an absolute path to scan a local directory:
- `/home/user/my-project`
- `~/projects/my-app` (will expand to home directory)
- `C:\Projects\MyApp` (Windows)

This is useful for:
- Private projects not hosted on any Git service
- Quick documentation during development
- Offline documentation generation

#### Git URLs (GitLab, Bitbucket, etc.)
Enter any Git-compatible URL to clone and scan:
- `https://gitlab.com/owner/repo`
- `https://bitbucket.org/owner/repo`
- `git@github.com:owner/repo.git`
- Self-hosted Git servers

> [!NOTE]
> Git URL scanning requires `git` to be installed and available in PATH.
> The repository will be cloned to a temporary directory for processing.

### MySQL Database Support

By default, OpenRepoWiki uses PostgreSQL. You can alternatively use MySQL as the database backend.

#### Configuration

1. Set the database engine in your `.env`:
   ```
   DB_ENGINE=mysql
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=openrepowiki
   DB_USER=root
   DB_PASSWORD=your_password
   ```

2. Update `docker-compose.yml` to use MySQL instead of PostgreSQL:
   ```yaml
   db:
     image: mysql:8.0
     environment:
       MYSQL_ROOT_PASSWORD: your_password
       MYSQL_DATABASE: openrepowiki
     ports:
       - "3306:3306"
   ```

3. Run the application with `docker compose up`.

> [!NOTE]
> When using MySQL, ensure your MySQL server uses `utf8mb4` character set for proper Unicode support.

## Requirements and Documentation

Refer [Documentation](https://github.com/daeisbae/open-repo-wiki/blob/main/docs/)
