# Fix Database Configuration

## Why
The current database configuration has two issues:
1. SQLite support was added for local development, but the requirement has changed - even local development should connect to remote database services
2. MySQL database migrations don't work correctly due to missing charset and options configuration
3. When tables already exist in the database but with a different structure, migration fails without helpful guidance

## What Changes

### Remove SQLite Support
- Remove SQLite configuration from `src/core_config/settings.py`
- Update `.env.example` and `.env.local.example` to remove SQLite references
- Update `README.md` to remove SQLite documentation
- Update `local-development` spec to remove SQLite requirement

### Fix MySQL Migration
- Add proper MySQL charset (`utf8mb4`) and collation settings
- Add `OPTIONS` configuration for MySQL connections
- Ensure `python manage.py migrate` works correctly with MySQL

### Table Structure Validation
- Create a custom management command `check_tables` to validate existing table structures
- Before migration, check if tables exist and compare their structure with expected DDL
- If structures match, proceed with migration
- If structures don't match, warn user to rename existing tables before retry

## Proposed Changes

### Backend - Settings
#### [MODIFY] [settings.py](file:///Users/vincentruan/PycharmProjects/open-repo-wiki/src/core_config/settings.py)
- Remove SQLite configuration block (lines 79-86)
- Add MySQL charset and options configuration

### Backend - Management Command
#### [NEW] `src/wiki_app/management/commands/check_tables.py`
- Custom command to check if tables exist
- Compare existing table columns with Django model fields
- Report mismatches and suggest renaming tables

### Backend - Migration Hook
#### [MODIFY] or [NEW] Pre-migration check
- Run table structure validation before applying migrations
- If mismatch found, abort with clear error message

### Configuration Files
#### [MODIFY] [.env.example](file:///Users/vincentruan/PycharmProjects/open-repo-wiki/.env.example)
- Remove `sqlite` from `DB_ENGINE` options

#### [MODIFY] [.env.local.example](file:///Users/vincentruan/PycharmProjects/open-repo-wiki/.env.local.example)
- Change from `DB_ENGINE=sqlite` to `DB_ENGINE=mysql` with connection details template

### Documentation
#### [MODIFY] [README.md](file:///Users/vincentruan/PycharmProjects/open-repo-wiki/README.md)
- Remove SQLite references from local development section
- Add documentation for table validation command

### Specs
#### [MODIFY] local-development spec
- Remove SQLite requirement, keep only synchronous task execution requirement

## Verification Plan

### Manual Verification
1. Run `python manage.py check_tables` on database with existing tables
2. Verify it detects structure mismatches
3. Run `python manage.py migrate` with MySQL and verify tables are created
4. Verify application starts with MySQL configuration
5. Verify application starts with PostgreSQL configuration

