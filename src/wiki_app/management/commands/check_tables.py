"""
Management command to check database table structures before migration.
Validates that existing tables match Django model definitions.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.apps import apps


class Command(BaseCommand):
    help = 'Check if database tables exist and if their structures match Django models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Show SQL commands to rename mismatched tables',
        )

    def handle(self, *args, **options):
        self.stdout.write('Checking database table structures...\n')
        
        # Get all models from wiki_app
        app_models = apps.get_app_config('wiki_app').get_models()
        
        mismatches = []
        missing_tables = []
        matching_tables = []
        
        for model in app_models:
            table_name = model._meta.db_table
            result = self._check_table(model, table_name)
            
            if result['status'] == 'missing':
                missing_tables.append(table_name)
            elif result['status'] == 'mismatch':
                mismatches.append(result)
            else:
                matching_tables.append(table_name)
        
        # Report results
        if matching_tables:
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Tables with matching structures ({len(matching_tables)}):'))
            for table in matching_tables:
                self.stdout.write(f'  - {table}')
        
        if missing_tables:
            self.stdout.write(self.style.WARNING(
                f'\n⚠ Tables not found ({len(missing_tables)}):'))
            for table in missing_tables:
                self.stdout.write(f'  - {table}')
            self.stdout.write('\n  These will be created during migration.')
        
        if mismatches:
            self.stdout.write(self.style.ERROR(
                f'\n✗ Tables with structure mismatches ({len(mismatches)}):'))
            
            for mismatch in mismatches:
                self.stdout.write(f'\n  Table: {mismatch["table"]}')
                
                if mismatch.get('missing_columns'):
                    self.stdout.write(self.style.WARNING(
                        f'    Missing columns: {", ".join(mismatch["missing_columns"])}'))
                
                if mismatch.get('extra_columns'):
                    self.stdout.write(self.style.WARNING(
                        f'    Extra columns: {", ".join(mismatch["extra_columns"])}'))
                
                if mismatch.get('type_mismatches'):
                    for col, info in mismatch['type_mismatches'].items():
                        self.stdout.write(self.style.WARNING(
                            f'    Column "{col}": expected {info["expected"]}, got {info["actual"]}'))
            
            self.stdout.write(self.style.ERROR(
                '\n⚠ MIGRATION WILL FAIL with these mismatches!'))
            self.stdout.write(
                '\nPlease rename the existing tables before running migrate:')
            
            for mismatch in mismatches:
                table = mismatch['table']
                backup_table = f'{table}_backup'
                if connection.vendor == 'mysql':
                    self.stdout.write(f'  RENAME TABLE `{table}` TO `{backup_table}`;')
                else:
                    self.stdout.write(f'  ALTER TABLE "{table}" RENAME TO "{backup_table}";')
            
            if options['fix']:
                self.stdout.write(self.style.WARNING(
                    '\n--fix flag detected, but automatic renaming is not implemented.'))
                self.stdout.write('Please run the SQL commands above manually.')
            
            raise CommandError('Table structure mismatches detected. See above for details.')
        
        self.stdout.write(self.style.SUCCESS('\n✓ All table structures are compatible with Django models.'))

    def _check_table(self, model, table_name):
        """Check if a table exists and compare its structure."""
        
        # Check if table exists
        with connection.cursor() as cursor:
            if connection.vendor == 'mysql':
                cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = %s",
                    [table_name]
                )
            elif connection.vendor == 'postgresql':
                cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = %s",
                    [table_name]
                )
            else:
                # SQLite fallback (should not be used anymore)
                cursor.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                    [table_name]
                )
            
            exists = cursor.fetchone()[0] > 0
        
        if not exists:
            return {'status': 'missing', 'table': table_name}
        
        # Get expected columns from Django model
        expected_columns = {}
        for field in model._meta.get_fields():
            if hasattr(field, 'column') and field.column:
                expected_columns[field.column] = self._get_field_type(field)
        
        # Get actual columns from database
        actual_columns = self._get_table_columns(table_name)
        
        # Compare
        missing_columns = set(expected_columns.keys()) - set(actual_columns.keys())
        extra_columns = set(actual_columns.keys()) - set(expected_columns.keys())
        
        # For now, we just check column presence, not types (types differ by DB)
        if missing_columns or extra_columns:
            return {
                'status': 'mismatch',
                'table': table_name,
                'missing_columns': list(missing_columns),
                'extra_columns': list(extra_columns),
                'type_mismatches': {}
            }
        
        return {'status': 'match', 'table': table_name}

    def _get_field_type(self, field):
        """Get a simplified type description for a Django field."""
        field_type = field.get_internal_type()
        return field_type

    def _get_table_columns(self, table_name):
        """Get columns from the database table."""
        columns = {}
        
        with connection.cursor() as cursor:
            if connection.vendor == 'mysql':
                cursor.execute(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() AND table_name = %s",
                    [table_name]
                )
            elif connection.vendor == 'postgresql':
                cursor.execute(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = %s",
                    [table_name]
                )
            else:
                # SQLite
                cursor.execute(f"PRAGMA table_info({table_name})")
                for row in cursor.fetchall():
                    columns[row[1]] = row[2]
                return columns
            
            for row in cursor.fetchall():
                columns[row[0]] = row[1]
        
        return columns
