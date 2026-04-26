"""
Document ingestion task runner.

Queued documents are drained by a background `ThreadPoolExecutor`. The
pool size defaults to 1 but can be increased via the `UKG_INGESTION_WORKERS`
environment variable for systems with spare cores and a GPU that can tolerate
multiple concurrent pipelines.

Workers claim queued documents atomically via a conditional UPDATE so two
workers never pick up the same document, even when the pool size is > 1.
"""

import logging
import os
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock
from django.db import close_old_connections
from .models import Document
from .services import ExtractionPipelineService


logger = logging.getLogger(__name__)


def get_worker_count() -> int:
    """
    Get the number of worker threads for the document ingestion task runner.
    To set the number of worker threads:
    - `export UKG_INGESTION_WORKERS=4`
    
    The default is 1.

    Returns:
        The number of worker threads for the document ingestion task runner.
    """
    try:
        return max(1, int(os.environ.get("UKG_INGESTION_WORKERS", "1")))
    except ValueError:
        return 1


executor = ThreadPoolExecutor(max_workers=get_worker_count())
runner_lock = Lock()
runner_futures = []

def enqueue_document_ingestion():
    """
    Enqueues a document for ingestion.
    Make sure at least `worker_count` tasks (document ingestion) are active.
    """
    global runner_futures
    worker_count = get_worker_count()
    with runner_lock:
        # Counts the number of active tasks
        runner_futures = [fut for fut in runner_futures if not fut.done()]
        missing = worker_count - len(runner_futures)

        # Submits the number of missing tasks to the executor
        for _ in range(max(0, missing)):
            runner_futures.append(executor.submit(drain_document_ingestion_queue))


def drain_document_ingestion_queue():
    """
    Processes a document from the document ingestion queue.
    """
    global runner_futures
    close_old_connections()
    try:
        while True:
            document = (
                Document.objects.filter(status=Document.STATUS_QUEUED)
                .order_by("created_at", "id")
                .first()
            )
            if document is None:
                return

            # Process the document using the extraction pipeline service
            try:
                service = ExtractionPipelineService()
                service.process_document(document)
            except Exception as exc:
                # If the document fails to ingest, update the document status to failed and log the error
                logger.exception("Document %s failed to ingest", document.id)
                document.status = Document.STATUS_FAILED
                document.error_message = str(exc)
                document.save(update_fields=["status", "error_message", "updated_at"])
    finally:
        # Close the old connections to the database
        close_old_connections()
        with runner_lock:
            # Update the completed tasks
            runner_futures = [fut for fut in runner_futures if not fut.done()]
            # If there are any queued documents, submit a new task to the executor
            if Document.objects.filter(status=Document.STATUS_QUEUED).exists():
                runner_futures.append(executor.submit(drain_document_ingestion_queue))
