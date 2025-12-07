# Tasks: Fix Database Configuration

- [x] **Remove SQLite Support**
    - [x] Remove SQLite configuration from `src/core_config/settings.py`. <!-- id: 0 -->
    - [x] Update `.env.example` to remove SQLite option. <!-- id: 1 -->
    - [x] Update `.env.local.example` with MySQL config template. <!-- id: 2 -->
    - [x] Update `README.md` to remove SQLite documentation. <!-- id: 3 -->

- [x] **Fix MySQL Configuration**
    - [x] Add charset (`utf8mb4`) and collation settings to MySQL config. <!-- id: 4 -->
    - [x] Add OPTIONS for MySQL connection. <!-- id: 5 -->

- [x] **Table Structure Validation**
    - [x] Create management command `check_tables` to validate table structures. <!-- id: 6 -->
    - [x] Implement column comparison with Django model fields. <!-- id: 7 -->
    - [x] Add warning message when structures don't match. <!-- id: 8 -->
    - [x] Integrate check into migration process. <!-- id: 9 -->

- [x] **Update Specs**
    - [x] Modify `local-development` spec to remove SQLite requirement. <!-- id: 10 -->
    - [x] Update `mysql-support` spec with charset requirement. <!-- id: 11 -->

- [x] **Validation**
    - [x] Test `python manage.py check_tables` on existing database. <!-- id: 12 -->
    - [x] Test `python manage.py migrate` with MySQL. <!-- id: 13 -->


