# Tasks: Add Local Development Support

- [x] **SQLite Database Support**
    - [x] Update `src/core_config/settings.py` to support `DB_ENGINE=sqlite`. <!-- id: 0 -->
    - [x] Update `.env.example` with SQLite option. <!-- id: 1 -->
    - [ ] Validation: Run `python manage.py migrate` with SQLite and verify tables are created. <!-- id: 2 -->

- [x] **Synchronous Task Execution**
    - [x] Create utility function `celery_available()` in `src/wiki_app/utils.py`. <!-- id: 3 -->
    - [x] Modify `src/wiki_app/tasks.py` to support synchronous execution fallback. <!-- id: 4 -->
    - [x] Update `src/wiki_app/views.py` to handle sync task execution in UI. <!-- id: 5 -->
    - [ ] Validation: Verify task runs synchronously when Redis is not available. <!-- id: 6 -->

- [x] **Documentation**
    - [x] Create `.env.local.example` template for local development. <!-- id: 7 -->
    - [x] Update `README.md` with "Local Development (No Docker)" section. <!-- id: 8 -->
    - [ ] Validation: Follow README instructions on a fresh setup and verify it works. <!-- id: 9 -->

