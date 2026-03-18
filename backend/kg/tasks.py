from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections

from .models import Document
from .services import ExtractionPipelineService


executor = ThreadPoolExecutor(max_workers=2)


def enqueue_document_ingestion(document_id: int) -> None:
    executor.submit(_run_document_ingestion, document_id)


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
