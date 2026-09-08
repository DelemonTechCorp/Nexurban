# nexurbanapp/management/commands/warm_properties_cache.py

import time

from django.core.management.base import BaseCommand

from nexurbanapp.services import refresh_all_properties_cache


class Command(BaseCommand):
    help = "Force-refresh the X-Opperp property list cache (bypasses TTL)."

    def handle(self, *args, **options):
        started = time.monotonic()

        try:
            props = refresh_all_properties_cache()
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Failed to refresh property cache: {e}")
            )
            return

        elapsed = time.monotonic() - started

        if not props:
            self.stdout.write(
                self.style.WARNING(
                    f"Cache refresh completed in {elapsed:.2f}s but returned 0 properties. "
                    "Check X_OPPERP_BASE_URL / X_OPPERP_API_KEY and upstream API health."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Cached {len(props)} properties in {elapsed:.2f}s"
            )
        )