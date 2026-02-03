from django.apps import AppConfig
import os


class WorkflowConfig(AppConfig):
    name = 'workflow'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """Start the scheduler when Django is ready"""
        # Only run scheduler in the main process (not in runserver reloader)
        if os.environ.get('RUN_MAIN') != 'true':
            return

        from . import scheduler
        try:
            scheduler.start_scheduler()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not start scheduler: {str(e)}")
