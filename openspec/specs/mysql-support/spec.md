# mysql-support Specification

## Purpose
Support for using MySQL as the database backend.

## Requirements
### Requirement: Support MySQL Database Engine
The application MUST support connecting to a MySQL database with proper charset configuration.

#### Scenario: Configure MySQL with UTF8MB4
Given the environment variable `DB_ENGINE` is set to `mysql`
And valid MySQL connection details (`DB_HOST`, `DB_USER`, etc.) are provided
When the application starts
Then it should connect using `utf8mb4` charset and proper SQL mode.

#### Scenario: MySQL Migration
Given the environment variable `DB_ENGINE` is set to `mysql`
When `python manage.py migrate` is executed
Then all database tables should be created successfully.

#### Scenario: Default to PostgreSQL
Given the `DB_ENGINE` environment variable is not set
When the application starts
Then it should default to using the PostgreSQL backend.


