from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Document, Triple, TripleEvidence
from .services import ExtractionPipelineService


class TripleUpsertTests(TestCase):
    def test_duplicate_triple_confidence_is_capped(self):
        document = Document.objects.create(
            file=SimpleUploadedFile("paper.pdf", b"%PDF-1.4 sample", content_type="application/pdf")
        )
        service = ExtractionPipelineService(src_dir="src")
        section_map = {}

        class TriplePayload:
            def __init__(self, conf):
                self.sub = "amyloid_beta"
                self.pred = "associated_with"
                self.obj = "alzheimers_disease"
                self.conf = conf
                self.source = "unit-test"
                self.section = ""

        service.upsert_triple(TriplePayload(0.7), document=document, section_map=section_map)
        service.upsert_triple(TriplePayload(0.6), document=document, section_map=section_map)

        triple = Triple.objects.get()
        self.assertEqual(1.0, triple.confidence)
        self.assertEqual(2, triple.support_count)
        self.assertEqual(2, TripleEvidence.objects.count())


class ApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("kg.views.enqueue_document_ingestion")
    def test_upload_endpoint_accepts_pdf(self, enqueue_mock):
        upload = SimpleUploadedFile("paper.pdf", b"%PDF-1.4 mock", content_type="application/pdf")
        response = self.client.post("/api/documents/upload", {"file": upload}, format="multipart")
        self.assertEqual(202, response.status_code)
        self.assertEqual(1, Document.objects.count())
        enqueue_mock.assert_called_once()

    def test_search_endpoint_highlights_entity_relations(self):
        triple = Triple.objects.create(
            subject_label="amyloid_beta",
            predicate_label="associated_with",
            object_label="alzheimers_disease",
            subject_norm="amyloid_beta",
            predicate_norm="associated_with",
            object_norm="alzheimers_disease",
            key="amyloid_beta|associated_with|alzheimers_disease",
            confidence=0.8,
            support_count=2,
        )

        entity_response = self.client.get("/api/search", {"q": "amyloid", "type": "entity"})
        self.assertEqual(200, entity_response.status_code)
        self.assertIn("triple-1", entity_response.data["highlight"]["edgeIds"])
        self.assertIn("amyloid_beta", entity_response.data["highlight"]["nodeIds"])

        relation_response = self.client.get("/api/search", {"q": "associated", "type": "relation"})
        self.assertEqual(200, relation_response.status_code)
        self.assertIn(f"triple-{triple.id}", relation_response.data["highlight"]["edgeIds"])
