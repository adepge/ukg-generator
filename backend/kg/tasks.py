"""
Document ingestion task runner.

Two modes are supported:

1. In-process (development): a ThreadPoolExecutor inside the Django
   process drains the queue. Convenient for manage.py runserver. Enabled
   by default whenever DEBUG=True (override with UKG_INGESTION_INPROC=1).

2. Standalone worker (production): a separate long-lived process runs
   the process_queue management command and drains the queue. Gunicorn
   workers therefore stay short-lived and never run multi-minute work
   that could be cut off by max-requests / timeout. Enabled by
   default whenever DEBUG=False (override with UKG_INGESTION_INPROC=0).
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from django.conf import settings
from django.db import close_old_connections

from .models import Document
from .services import ExtractionPipelineService


logger = logging.getLogger(__name__)


def get_worker_count() -> int:
    """
    Get the number of in-process worker threads.

    Set via UKG_INGESTION_WORKERS=4. Defaults to 1.
    """
    try:
        return max(1, int(os.environ.get("UKG_INGESTION_WORKERS", "1")))
    except ValueError:
        return 1


def in_process_enabled() -> bool:
    """
    Whether to drain the queue inside the current Django process.

    Defaults to True in DEBUG (in production, run a separate manage.py process_queue worker).
    """
    raw = os.environ.get("UKG_INGESTION_INPROC")
    if raw is None:
        return bool(getattr(settings, "DEBUG", False))
    return raw == "1"


# ---------------------------------------------------------------------------
# Standalone-worker entry point (also reused by the in-process executor)
# ---------------------------------------------------------------------------

def drain_document_ingestion_queue() -> int:
    """
    Drain queued documents in the calling thread until the queue is empty.

    Returns the number of documents processed (successful or failed).
    """
    close_old_connections()
    processed = 0
    try:
        while True:
            document = (
                Document.objects.filter(status=Document.STATUS_QUEUED)
                .order_by("created_at", "id")
                .first()
            )
            if document is None:
                return processed

            try:
                service = ExtractionPipelineService()
                service.process_document(document)
            except Exception as exc:
                logger.exception("Document %s failed to ingest", document.id)
                document.status = Document.STATUS_FAILED
                document.error_message = str(exc)
                document.save(
                    update_fields=["status", "error_message", "updated_at"]
                )
            processed += 1
    finally:
        close_old_connections()


# ---------------------------------------------------------------------------
# In-process executor (development only by default)
# ---------------------------------------------------------------------------

executor: ThreadPoolExecutor | None = None
executor_lock = Lock()
runner_futures: list = []


def get_executor() -> ThreadPoolExecutor:
    """Lazily create the shared in-process ThreadPoolExecutor."""
    global executor
    if executor is None:
        with executor_lock:
            if executor is None:
                executor = ThreadPoolExecutor(
                    max_workers=get_worker_count(),
                    thread_name_prefix="ukg-ingest",
                )
    return executor


def drain_and_resubmit() -> None:
    """
    In-process executor task. Drains the queue once, then re-submits
    itself if more documents arrived during the drain (covers the race
    between a finishing drain and a new upload).
    """
    try:
        drain_document_ingestion_queue()
    finally:
        with executor_lock:
            global runner_futures
            runner_futures = [f for f in runner_futures if not f.done()]
            if Document.objects.filter(status=Document.STATUS_QUEUED).exists():
                runner_futures.append(
                    executor.submit(drain_and_resubmit)
                )


def enqueue_document_ingestion() -> None:
    """
    Notify the ingestion runtime that a new document is queued.

    In-process mode: ensure `get_worker_count()` drain tasks are active.
    Standalone-worker mode: no-op (the worker polls the DB; it'll pick the
    document up within its poll interval, default ~2s).
    """
    if not in_process_enabled():
        return

    worker_count = get_worker_count()
    with executor_lock:
        global runner_futures
        runner_futures = [f for f in runner_futures if not f.done()]
        missing = worker_count - len(runner_futures)
        executor = get_executor().submit(drain_and_resubmit)
        for _ in range(max(0, missing)):
            runner_futures.append(executor.submit(drain_and_resubmit))
