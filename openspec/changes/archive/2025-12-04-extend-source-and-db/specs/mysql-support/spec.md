# MySQL Database Support

## ADDED Requirements

### Requirement: Support MySQL Database Engine
The application MUST support connecting to a MySQL database when configured via environment variables.

#### Scenario: Configure MySQL
Given the environment variable `DB_ENGINE` is set to `mysql`
And valid MySQL connection details (`DB_HOST`, `DB_USER`, etc.) are provided
When the application starts
Then it should successfully connect to the MySQL database.

#### Scenario: Default to PostgreSQL
Given the `DB_ENGINE` environment variable is not set
When the application starts
Then it should default to using the PostgreSQL backend.
