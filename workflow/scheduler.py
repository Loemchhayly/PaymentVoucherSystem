"""
APScheduler configuration for automatic database backups
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


def run_database_backup():
    """Run the database backup command"""
    try:
        logger.info("Starting scheduled database backup...")
        call_command('backup_database')
        logger.info("Scheduled database backup completed successfully")
    except Exception as e:
        logger.error(f"Scheduled database backup failed: {str(e)}")


def start_scheduler():
    """Start the APScheduler for automatic backups"""
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # Schedule daily backup at midnight
    scheduler.add_job(
        run_database_backup,
        trigger=CronTrigger(hour=0, minute=0),  # Run at midnight (00:00)
        id="daily_database_backup",
        max_instances=1,
        replace_existing=True,
        jobstore="default",
        name="Daily Database Backup"
    )

    try:
        logger.info("Starting APScheduler for automatic database backups...")
        scheduler.start()
        logger.info("APScheduler started successfully. Daily backups scheduled for midnight.")
    except Exception as e:
        logger.error(f"Failed to start APScheduler: {str(e)}")
