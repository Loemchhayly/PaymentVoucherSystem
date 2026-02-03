# Database Backup Setup Guide

## Overview

This project includes a fully automatic database backup system that runs inside Django using APScheduler. Backups are created automatically every day at midnight, tracked in the database, and can be viewed/managed through the Django admin interface.

## Features

- **Fully Automatic**: Runs inside Django, no external schedulers needed
- **Web Interface**: View and manage backups through Django admin
- **Database Tracking**: All backups are logged in the database with status, size, and duration
- **Supports Multiple Databases**: Works with both SQLite and PostgreSQL
- **Automatic Cleanup**: Old backups are automatically deleted after 30 days
- **PostgreSQL Compression**: PostgreSQL backups are compressed with gzip to save space
- **Error Tracking**: Failed backups are logged with error messages

## Quick Start

The backup system is **already configured and running automatically**. When you start your Django server, backups will be created daily at midnight.

Just run your Django server:
```bash
python manage.py runserver
```

The scheduler will start automatically and create daily backups.

## Configuration

The backup settings are in `settings.py`:

```python
# Database Backup Configuration
BACKUP_DIR = BASE_DIR / 'backups'
BACKUP_RETENTION_DAYS = 30  # Keep backups for 30 days
```

You can modify these settings as needed.

## Viewing Backups

### Django Admin Interface

1. Go to the Django admin: http://localhost:8000/admin/
2. Navigate to **Workflow** → **Backup histories**
3. You'll see a list of all backups with:
   - Status (Success/Failed/In Progress)
   - Database type (SQLite/PostgreSQL)
   - File name and size
   - Backup duration
   - Download link

The admin interface shows:
- Green dot (●) for successful backups
- Red dot (●) for failed backups
- Orange dot (●) for backups in progress

### Backup Files

Backups are stored in the `backups/` directory:
- **SQLite**: `sqlite_backup_YYYYMMDD_HHMMSS.db`
- **PostgreSQL**: `postgres_backup_YYYYMMDD_HHMMSS.sql.gz` (compressed)

Example:
```
backups/
├── sqlite_backup_20260203_000001.db
├── sqlite_backup_20260202_000001.db
├── sqlite_backup_20260201_000001.db
```

## Manual Backup

To create a backup manually:

```bash
python manage.py backup_database
```

### Command Options

```bash
# Create backup with 60-day retention
python manage.py backup_database --retention-days 60

# Create backup without cleaning old ones
python manage.py backup_database --no-cleanup
```

## How It Works

### Automatic Scheduling

1. **APScheduler** runs inside Django (no external services needed)
2. Scheduler starts automatically when Django starts
3. Backup runs every day at **midnight (00:00)**
4. Each backup is logged in the database
5. Old backups are automatically deleted after 30 days

### Scheduler Configuration

The scheduler is configured in `workflow/scheduler.py`:
- Uses `CronTrigger` for daily execution at midnight
- Runs in background without blocking Django
- Stores job information in Django database

### Backup Process

1. Creates `BackupHistory` record with "In Progress" status
2. Performs backup based on database type:
   - **SQLite**: Copies database file
   - **PostgreSQL**: Runs `pg_dump` and compresses with gzip
3. Records file size, duration, and file path
4. Updates status to "Success" or "Failed"
5. Cleans up old backups beyond retention period

## Backup Schedule

By default, backups run at **midnight (00:00)** every day.

To change the schedule, edit `workflow/scheduler.py`:

```python
# Daily at 2:00 AM
scheduler.add_job(
    run_database_backup,
    trigger=CronTrigger(hour=2, minute=0),
    ...
)

# Every 6 hours
scheduler.add_job(
    run_database_backup,
    trigger=CronTrigger(hour='*/6'),
    ...
)

# Every Sunday at midnight
scheduler.add_job(
    run_database_backup,
    trigger=CronTrigger(day_of_week='sun', hour=0, minute=0),
    ...
)
```

After changing the schedule, restart your Django server.

## Restoring from Backup

### SQLite

```bash
# Stop the Django server first
# Copy the backup file over your current database
copy backups\sqlite_backup_YYYYMMDD_HHMMSS.db db.sqlite3

# Or on Linux/Mac:
cp backups/sqlite_backup_YYYYMMDD_HHMMSS.db db.sqlite3
```

### PostgreSQL

```bash
# Decompress the backup first
gunzip -k backups/postgres_backup_YYYYMMDD_HHMMSS.sql.gz

# Restore the database
psql -h localhost -U your_user -d your_database -f backups/postgres_backup_YYYYMMDD_HHMMSS.sql

# Or on Windows:
psql -h localhost -U your_user -d your_database -f backups\postgres_backup_YYYYMMDD_HHMMSS.sql
```

## Monitoring Backups

### Check Backup Status

1. **Django Admin**: Go to Workflow → Backup histories
2. **Log Files**: Check Django logs for backup messages
3. **Database Query**: Query the `BackupHistory` model

### Check Recent Backups

```python
# In Django shell (python manage.py shell)
from workflow.models import BackupHistory

# Get last 5 backups
recent_backups = BackupHistory.objects.all()[:5]
for backup in recent_backups:
    print(f"{backup.created_at}: {backup.status} - {backup.file_name}")
```

### Check for Failed Backups

```python
# In Django shell
from workflow.models import BackupHistory

failed_backups = BackupHistory.objects.filter(status='FAILED')
for backup in failed_backups:
    print(f"{backup.created_at}: {backup.error_message}")
```

## Troubleshooting

### Backups Not Running Automatically

**Issue**: No backups are being created at midnight

**Solutions**:
1. Ensure Django server is running (backups only run when server is running)
2. Check Django logs for scheduler startup messages
3. Verify `workflow` app is in `INSTALLED_APPS` in settings.py
4. Restart Django server to reinitialize scheduler

### PostgreSQL Backup Issues

**Issue**: `pg_dump not found`

**Solution**:
- Install PostgreSQL client tools
- Add PostgreSQL bin directory to system PATH
- On Windows: `C:\Program Files\PostgreSQL\15\bin`
- Restart terminal/command prompt

**Issue**: `Authentication failed`

**Solution**:
- Verify database credentials in `.env` file
- Ensure PostgreSQL is running
- Check user has backup permissions

### Disk Space Issues

**Issue**: Running out of disk space

**Solutions**:
1. Reduce `BACKUP_RETENTION_DAYS` in settings.py
2. Manually delete old backups from `backups/` directory
3. Move backups to external storage or cloud
4. For PostgreSQL, backups are automatically compressed

### Scheduler Not Starting

**Issue**: Scheduler doesn't start when Django starts

**Solution**:
1. Check for errors in Django startup logs
2. Ensure `django_apscheduler` is in `INSTALLED_APPS`
3. Run migrations: `python manage.py migrate`
4. Check `workflow/apps.py` has the `ready()` method

## Production Deployment

For production environments:

### 1. Use a Process Manager

Use a process manager to keep Django running 24/7:

**Supervisor (Linux)**:
```ini
[program:payment_voucher]
command=/path/to/env/bin/python manage.py runserver 0.0.0.0:8000
directory=/path/to/PaymentVoucherSystem
user=www-data
autostart=true
autorestart=true
```

**Windows Service** (using NSSM):
```bash
nssm install PaymentVoucherSystem "C:\path\to\env\Scripts\python.exe" "C:\path\to\manage.py runserver"
```

### 2. Cloud Storage Backups

Copy backups to cloud storage for redundancy:

**AWS S3**:
```python
# Add to workflow/scheduler.py after backup
import boto3
s3 = boto3.client('s3')
s3.upload_file(backup_file, 'your-bucket', f'backups/{filename}')
```

**Google Cloud Storage**:
```python
from google.cloud import storage
client = storage.Client()
bucket = client.bucket('your-bucket')
blob = bucket.blob(f'backups/{filename}')
blob.upload_from_filename(backup_file)
```

### 3. Monitoring & Alerts

Set up email alerts for failed backups:

```python
# In workflow/scheduler.py
from django.core.mail import mail_admins

def run_database_backup():
    try:
        call_command('backup_database')
    except Exception as e:
        mail_admins(
            'Backup Failed',
            f'Database backup failed: {str(e)}'
        )
        raise
```

### 4. Regular Restore Testing

Regularly test your backups to ensure they work:
- Restore to a test database monthly
- Verify data integrity
- Document restore procedures

## Security Considerations

1. **Permissions**: Backups contain sensitive data
   - Set proper file permissions: `chmod 600 backups/*`
   - Restrict admin access to backup history

2. **Encryption**: For sensitive data
   - Encrypt backups before storing
   - Use encrypted cloud storage

3. **Git Exclusion**: Backups are excluded from git via `.gitignore`

4. **Credentials**: PostgreSQL credentials are passed securely via environment variables

## Advanced Configuration

### Custom Backup Location

```python
# In settings.py
BACKUP_DIR = Path('/var/backups/payment_voucher')
```

### Multiple Backup Schedules

```python
# In workflow/scheduler.py
# Daily full backup at midnight
scheduler.add_job(
    run_database_backup,
    trigger=CronTrigger(hour=0, minute=0),
    id="daily_backup",
    ...
)

# Additional backup every 6 hours
scheduler.add_job(
    run_database_backup,
    trigger=CronTrigger(hour='*/6'),
    id="hourly_backup",
    ...
)
```

### Webhook Notifications

```python
# In workflow/scheduler.py
import requests

def run_database_backup():
    try:
        call_command('backup_database')
        requests.post('https://your-webhook-url.com/backup-success')
    except Exception as e:
        requests.post('https://your-webhook-url.com/backup-failed',
                     json={'error': str(e)})
```

## FAQ

**Q: Do I need to keep Django running for backups to work?**
A: Yes, Django must be running for automatic backups. Use a process manager in production.

**Q: Can I change the backup time?**
A: Yes, edit `workflow/scheduler.py` and modify the `CronTrigger` parameters.

**Q: How do I backup immediately?**
A: Run `python manage.py backup_database` from the command line.

**Q: Where can I download backups?**
A: From Django admin (Workflow → Backup histories) or directly from the `backups/` folder.

**Q: What happens if a backup fails?**
A: The error is logged in the database and visible in Django admin.

**Q: Can I disable automatic backups?**
A: Yes, comment out the `scheduler.start()` line in `workflow/apps.py`.

## Support

For issues or questions:
1. Check Django logs for error messages
2. Verify scheduler is running: Check admin → Django Apscheduler → Django jobs
3. Test manual backup: `python manage.py backup_database`
4. Check backup history in admin for error messages
