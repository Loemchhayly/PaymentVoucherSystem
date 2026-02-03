"""
Django management command for automatic database backups.
Supports both SQLite and PostgreSQL databases.
"""
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from django.utils import timezone
from workflow.models import BackupHistory


class Command(BaseCommand):
    help = 'Create a backup of the database and clean up old backups'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-cleanup',
            action='store_true',
            help='Skip cleanup of old backups',
        )
        parser.add_argument(
            '--retention-days',
            type=int,
            default=getattr(settings, 'BACKUP_RETENTION_DAYS', 30),
            help='Number of days to keep backups (default: 30)',
        )

    def handle(self, *args, **options):
        """Execute the backup process"""
        start_time = time.time()
        backup_history = None

        try:
            # Get backup directory from settings
            backup_dir = Path(getattr(
                settings,
                'BACKUP_DIR',
                settings.BASE_DIR / 'backups'
            ))

            # Create backup directory if it doesn't exist
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Generate timestamp for backup filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Perform backup based on database type
            db_config = settings.DATABASES['default']
            engine = db_config['ENGINE']

            # Determine database type
            if 'sqlite' in engine:
                db_type = 'SQLITE'
            elif 'postgresql' in engine:
                db_type = 'POSTGRESQL'
            else:
                self.stdout.write(
                    self.style.ERROR(f'Unsupported database engine: {engine}')
                )
                return

            # Create backup history record
            backup_history = BackupHistory.objects.create(
                status='IN_PROGRESS',
                database_type=db_type,
                file_name='',  # Will be updated after backup
                file_path=''
            )

            # Perform the backup
            if db_type == 'SQLITE':
                backup_file = self.backup_sqlite(backup_dir, timestamp, db_config)
            else:
                backup_file = self.backup_postgresql(backup_dir, timestamp, db_config)

            # Get file size
            file_size = backup_file.stat().st_size

            # Update backup history with success
            duration = time.time() - start_time
            backup_history.status = 'SUCCESS'
            backup_history.file_name = backup_file.name
            backup_history.file_path = str(backup_file)
            backup_history.file_size = file_size
            backup_history.duration_seconds = duration
            backup_history.save()

            # Cleanup old backups if not disabled
            if not options['no_cleanup']:
                self.cleanup_old_backups(backup_dir, options['retention_days'])

            self.stdout.write(
                self.style.SUCCESS(
                    f'Backup created successfully: {backup_file}\n'
                    f'Size: {backup_history.get_file_size_display()}\n'
                    f'Duration: {duration:.2f} seconds'
                )
            )

        except Exception as e:
            # Update backup history with failure
            if backup_history:
                backup_history.status = 'FAILED'
                backup_history.error_message = str(e)
                backup_history.duration_seconds = time.time() - start_time
                backup_history.save()

            self.stdout.write(
                self.style.ERROR(f'Backup failed: {str(e)}')
            )
            raise

    def backup_sqlite(self, backup_dir, timestamp, db_config):
        """Backup SQLite database"""
        db_path = Path(db_config['NAME'])

        if not db_path.exists():
            raise FileNotFoundError(f'Database file not found: {db_path}')

        # Create backup filename
        backup_file = backup_dir / f'sqlite_backup_{timestamp}.db'

        # Close all database connections
        connection.close()

        # Copy the database file
        shutil.copy2(db_path, backup_file)

        self.stdout.write(f'SQLite database backed up to: {backup_file}')

        return backup_file

    def backup_postgresql(self, backup_dir, timestamp, db_config):
        """Backup PostgreSQL database"""
        backup_file = backup_dir / f'postgres_backup_{timestamp}.sql'

        # Build pg_dump command
        env = os.environ.copy()
        env['PGPASSWORD'] = db_config['PASSWORD']

        cmd = [
            'pg_dump',
            '-h', db_config.get('HOST', 'localhost'),
            '-p', str(db_config.get('PORT', '5432')),
            '-U', db_config['USER'],
            '-d', db_config['NAME'],
            '-F', 'p',  # Plain text format
            '-f', str(backup_file),
        ]

        # Execute pg_dump
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            self.stdout.write(f'PostgreSQL database backed up to: {backup_file}')

            # Compress the backup to save space
            import gzip
            compressed_file = Path(f'{backup_file}.gz')

            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove uncompressed file
            backup_file.unlink()

            self.stdout.write(f'Backup compressed: {compressed_file}')

            return compressed_file

        except subprocess.CalledProcessError as e:
            raise Exception(f'pg_dump failed: {e.stderr}')
        except FileNotFoundError:
            raise Exception(
                'pg_dump not found. Make sure PostgreSQL client tools are installed '
                'and in your system PATH.'
            )

    def cleanup_old_backups(self, backup_dir, retention_days):
        """Remove backups older than retention_days"""
        cutoff_date = timezone.now() - timedelta(days=retention_days)

        deleted_count = 0

        # Find all backup files
        for backup_file in backup_dir.glob('*_backup_*'):
            # Get file modification time (make timezone-aware)
            file_time = timezone.make_aware(
                datetime.fromtimestamp(backup_file.stat().st_mtime)
            )

            # Delete if older than retention period
            if file_time < cutoff_date:
                # Delete database record if exists
                BackupHistory.objects.filter(file_path=str(backup_file)).delete()

                # Delete the file
                backup_file.unlink()
                deleted_count += 1
                self.stdout.write(f'Deleted old backup: {backup_file.name}')

        # Also clean up orphaned database records (files that no longer exist)
        orphaned_records = BackupHistory.objects.filter(created_at__lt=cutoff_date)
        for record in orphaned_records:
            if record.file_path and not Path(record.file_path).exists():
                record.delete()

        if deleted_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Cleaned up {deleted_count} old backup(s) '
                    f'(older than {retention_days} days)'
                )
            )
        else:
            self.stdout.write('No old backups to clean up')
