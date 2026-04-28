"""
Long-lived document ingestion worker.

Run as a separate systemd service in production so that gunicorn workers
stay short-lived and never get killed mid-document by `--max-requests`
or `--timeout`. See `tasks.py` for the architectural rationale.

    python manage.py process_queue [--poll-interval 2.0] [--once]
"""

import logging
import signal
import time

from django.core.management.base import BaseCommand

from kg.tasks import drain_document_ingestion_queue


class Command(BaseCommand):
    help = (
        "Drain the document ingestion queue. Runs forever as a worker "
        "process; SIGTERM / SIGINT trigger a graceful stop after the "
        "current document finishes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--poll-interval",
            type=float,
            default=2.0,
            help="Seconds to sleep between empty-queue checks (default: 2.0).",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Drain the queue once and exit (useful for cron / tests).",
        )

    def handle(self, *args, **options) -> None:
        poll_interval: float = options["poll_interval"]
        run_once: bool = options["once"]

        self._stop = False
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        logger = logging.getLogger("ukg.worker")
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
                )
            )
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

        logger.info(
            "UKG worker starting (poll_interval=%ss, once=%s)",
            poll_interval,
            run_once,
        )

        try:
            while not self._stop:
                processed = drain_document_ingestion_queue()
                if processed:
                    logger.info("Drained %s document(s)", processed)
                if run_once:
                    break
                # Interruptible sleep so SIGTERM is honoured promptly.
                slept = 0.0
                while slept < poll_interval and not self._stop:
                    time.sleep(min(0.5, poll_interval - slept))
                    slept += 0.5
        finally:
            logger.info("UKG worker stopped")

    def _handle_signal(self, signum, _frame) -> None:
        self._stop = True
