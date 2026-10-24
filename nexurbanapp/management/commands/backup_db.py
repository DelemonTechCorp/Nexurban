# nexurbanapp/management/commands/backup_db.py
#
# Appends a full snapshot of every model to ONE backup file, one line per day:
#   {"date": "2026-10-24", "created_at": "...", "records": 123, "data": [...]}
#
#   python manage.py backup_db                      # today's snapshot (skips if already done)
#   python manage.py backup_db --force              # add another snapshot for today anyway
#   python manage.py backup_db --list               # show snapshots in the file
#   python manage.py backup_db --restore 2026-10-24 # load that day's snapshot into the DB

import io
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core import serializers
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# Rebuilt automatically by Django / not real data
EXCLUDE = ["contenttypes", "auth.permission", "sessions", "admin.logentry"]


def backup_path():
    return Path(settings.BACKUP_FILE)


def today_str():
    return datetime.now(ZoneInfo(settings.BACKUP_TIMEZONE)).strftime("%Y-%m-%d")


def iter_snapshots(path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def has_snapshot_for(path, date):
    if not path.exists():
        return False
    prefix = f'{{"date": "{date}"'
    with path.open("r", encoding="utf-8") as f:
        return any(line.startswith(prefix) for line in f)


class Command(BaseCommand):
    help = "Append today's snapshot of all models to the single daily backup file."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Back up even if today is already saved.")
        parser.add_argument("--list", action="store_true", help="List snapshots in the backup file.")
        parser.add_argument("--restore", metavar="YYYY-MM-DD", help="Restore the snapshot for this date.")

    def handle(self, *args, **options):
        path = backup_path()

        if options["list"]:
            return self.list_snapshots(path)

        if options["restore"]:
            return self.restore(path, options["restore"])

        self.backup(path, force=options["force"])

    def backup(self, path, force=False):
        date = today_str()

        if not force and has_snapshot_for(path, date):
            self.stdout.write(self.style.WARNING(f"Backup for {date} already exists in {path}, skipping."))
            return

        out = io.StringIO()
        call_command(
            "dumpdata",
            exclude=EXCLUDE,
            natural_foreign=True,
            natural_primary=True,
            stdout=out,
        )
        data = json.loads(out.getvalue() or "[]")

        entry = {
            "date": date,
            "created_at": datetime.now(ZoneInfo(settings.BACKUP_TIMEZONE)).isoformat(timespec="seconds"),
            "records": len(data),
            "data": data,
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())

        self.stdout.write(self.style.SUCCESS(f"Backed up {len(data)} records for {date} -> {path}"))

    def list_snapshots(self, path):
        found = False
        for snap in iter_snapshots(path):
            found = True
            self.stdout.write(f"{snap['date']}  {snap['created_at']}  {snap['records']} records")
        if not found:
            self.stdout.write(self.style.WARNING(f"No snapshots in {path}"))

    def restore(self, path, date):
        # Latest snapshot for that date wins (in case --force added more than one)
        snapshot = None
        for snap in iter_snapshots(path):
            if snap["date"] == date:
                snapshot = snap

        if snapshot is None:
            raise CommandError(f"No snapshot for {date} in {path}")

        objects = serializers.deserialize(
            "json",
            json.dumps(snapshot["data"]),
            handle_forward_references=True,
        )

        count = 0
        with transaction.atomic():
            for obj in objects:
                obj.save()
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Restored {count} records from {date}"))
