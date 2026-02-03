@echo off
REM Automated database backup script for Windows Task Scheduler
REM This script activates the virtual environment and runs the backup command

cd /d "%~dp0"

REM Activate virtual environment
call env\Scripts\activate.bat

REM Run the backup command
python manage.py backup_database

REM Deactivate virtual environment
deactivate

REM Log completion time
echo Backup completed at %date% %time% >> backups\backup_log.txt
