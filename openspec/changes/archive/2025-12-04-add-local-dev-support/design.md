# Design: Local Development Support

## Problem
Currently, the application requires:
1. **PostgreSQL** - For data storage
2. **Redis** - As Celery message broker
3. **Celery worker** - For async task processing

This makes local development setup complex and resource-heavy.

## Solution Overview

### 1. SQLite Database Support
Add SQLite as a third database engine option (alongside PostgreSQL and MySQL).

```python
DB_ENGINE = env('DB_ENGINE', default='postgres')

if DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
elif DB_ENGINE == 'mysql':
    # ... existing mysql config
else:
    # ... existing postgres config
```

### 2. Synchronous Task Execution
When Redis is not available, execute tasks synchronously instead of queuing them.

```python
# In tasks.py
def process_repository_task(owner, repo):
    if not celery_available():
        # Run synchronously
        return _process_repository_sync(owner, repo)
    else:
        # Queue for async processing
        return _process_repository_async.delay(owner, repo)
```

### 3. Celery Availability Detection
```python
def celery_available():
    try:
        from celery import current_app
        current_app.control.ping(timeout=0.5)
        return True
    except:
        return False
```

## Trade-offs

| Aspect | Docker Mode | Local Dev Mode |
|--------|-------------|----------------|
| Database | PostgreSQL/MySQL | SQLite |
| Task Processing | Async (Celery) | Sync (blocking) |
| Setup Complexity | Higher | Lower |
| Performance | Production-ready | Development only |
| Concurrent Requests | Supported | Limited |

## Migration Path
- Local development uses SQLite by default
- Production/Docker continues using PostgreSQL
- No changes to existing Docker workflow
