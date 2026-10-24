# nexurbanapp/management/commands/run_backup_scheduler.py
#
# Long-running process that calls `backup_db` every day at BACKUP_TIME.
# Keep it running alongside the site (systemd / supervisor / pm2 / Task Scheduler "at startup").
#
#   python manage.py run_backup_scheduler
#   python manage.py run_backup_scheduler --time 23:30

import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run the daily DB backup automatically at a fixed time every day."

    def add_arguments(self, parser):
        parser.add_argument("--time", default=settings.BACKUP_TIME, help="Daily run time, HH:MM (24h).")

    def handle(self, *args, **options):
        try:
            hour, minute = (int(x) for x in options["time"].split(":"))
        except ValueError:
            raise CommandError("--time must be HH:MM, e.g. 02:00")

        tz = ZoneInfo(settings.BACKUP_TIMEZONE)
        self.stdout.write(f"Backup scheduler started: daily at {hour:02d}:{minute:02d} ({tz.key})")

        # Catch up if the process starts after today's time (backup_db skips if already done)
        now = datetime.now(tz)
        if now >= now.replace(hour=hour, minute=minute, second=0, microsecond=0):
            self.run_backup()

        while True:
            now = datetime.now(tz)
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)

            self.stdout.write(f"Next backup at {next_run.isoformat(timespec='minutes')}")

            # Sleep in short steps so clock changes / laptop sleep don't throw it off
            while datetime.now(tz) < next_run:
                time.sleep(min(60, max(1, (next_run - datetime.now(tz)).total_seconds())))

            self.run_backup()

    def run_backup(self):
        try:
            call_command("backup_db", stdout=self.stdout, stderr=self.stderr)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Backup failed: {e}"))
