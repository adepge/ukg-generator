from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock

from django.db import close_old_connections

from .models import Document
from .services import ExtractionPipelineService


executor = ThreadPoolExecutor(max_workers=1)
runner_lock = Lock()
runner_future: Future | None = None


def enqueue_document_ingestion(document_id: int) -> None:
    del document_id
    _ensure_ingestion_runner()


def _ensure_ingestion_runner() -> None:
    global runner_future
    with runner_lock:
        if runner_future is not None and not runner_future.done():
            return
        runner_future = executor.submit(_drain_document_ingestion_queue)


def _drain_document_ingestion_queue() -> None:
    global runner_future
    close_old_connections()
    try:
        while True:
            document = (
                Document.objects.filter(status=Document.STATUS_QUEUED).order_by("created_at", "id").first()
            )
            if document is None:
                return
            _run_document_ingestion(document.id)
    finally:
        close_old_connections()
        with runner_lock:
            runner_future = None
            if Document.objects.filter(status=Document.STATUS_QUEUED).exists():
                runner_future = executor.submit(_drain_document_ingestion_queue)


def _run_document_ingestion(document_id: int) -> None:
    close_old_connections()
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return

    try:
        service = ExtractionPipelineService()
        service.process_document(document)
    except Exception as exc:
        document.status = Document.STATUS_FAILED
        document.error_message = str(exc)
        document.save(update_fields=["status", "error_message", "updated_at"])
    finally:
        close_old_connections()
