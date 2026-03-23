from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from . import tasks
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
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/documents/upload", {"file": upload}, format="multipart")
        self.assertEqual(202, response.status_code)
        self.assertEqual(1, Document.objects.count())
        enqueue_mock.assert_called_once()
        self.assertEqual(1, len(response.data["documents"]))

    @patch("kg.views.enqueue_document_ingestion")
    def test_upload_endpoint_accepts_multiple_pdfs_before_enqueuing_processing(self, enqueue_mock):
        first_upload = SimpleUploadedFile("first.pdf", b"%PDF-1.4 first", content_type="application/pdf")
        second_upload = SimpleUploadedFile("second.pdf", b"%PDF-1.4 second", content_type="application/pdf")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/documents/upload",
                {"files": [first_upload, second_upload]},
                format="multipart",
            )

        self.assertEqual(202, response.status_code)
        self.assertEqual(2, Document.objects.count())
        self.assertEqual(2, len(response.data["documents"]))
        enqueue_mock.assert_called_once()

    def test_search_endpoint_highlights_entity_relations(self):
        higher_confidence_triple = Triple.objects.create(
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
        lower_confidence_triple = Triple.objects.create(
            subject_label="amyloid_precursor",
            predicate_label="linked_to",
            object_label="plaques",
            subject_norm="amyloid_precursor",
            predicate_norm="linked_to",
            object_norm="plaques",
            key="amyloid_precursor|linked_to|plaques",
            confidence=0.4,
            support_count=1,
        )

        entity_response = self.client.get("/api/search", {"q": "amyloid", "type": "entity"})
        self.assertEqual(200, entity_response.status_code)
        self.assertIn(f"triple-{higher_confidence_triple.id}", entity_response.data["highlight"]["edgeIds"])
        self.assertIn("amyloid_beta", entity_response.data["highlight"]["nodeIds"])
        self.assertEqual(
            [higher_confidence_triple.id, lower_confidence_triple.id],
            [match["id"] for match in entity_response.data["matches"]],
        )
        self.assertEqual(
            [0.8, 0.4],
            [match["confidence"] for match in entity_response.data["matches"]],
        )

        relation_response = self.client.get("/api/search", {"q": "associated", "type": "relation"})
        self.assertEqual(200, relation_response.status_code)
        self.assertIn(f"triple-{higher_confidence_triple.id}", relation_response.data["highlight"]["edgeIds"])

    def test_graph_endpoint_limits_edges_by_confidence(self):
        top_triple = Triple.objects.create(
            subject_label="alpha",
            predicate_label="related_to",
            object_label="beta",
            subject_norm="alpha",
            predicate_norm="related_to",
            object_norm="beta",
            key="alpha|related_to|beta",
            confidence=0.9,
            support_count=2,
        )
        Triple.objects.create(
            subject_label="gamma",
            predicate_label="related_to",
            object_label="delta",
            subject_norm="gamma",
            predicate_norm="related_to",
            object_norm="delta",
            key="gamma|related_to|delta",
            confidence=0.3,
            support_count=1,
        )

        response = self.client.get("/api/graph", {"limit": 1})

        self.assertEqual(200, response.status_code)
        self.assertEqual(2, response.data["meta"]["totalEdges"])
        self.assertEqual(1, response.data["meta"]["returnedEdges"])
        self.assertTrue(response.data["meta"]["limited"])
        self.assertEqual([f"triple-{top_triple.id}"], [edge["data"]["id"] for edge in response.data["edges"]])

    def test_graph_endpoint_filters_edges_by_min_confidence(self):
        passing_triple = Triple.objects.create(
            subject_label="alpha",
            predicate_label="related_to",
            object_label="beta",
            subject_norm="alpha",
            predicate_norm="related_to",
            object_norm="beta",
            key="alpha|related_to|beta|high",
            confidence=0.9,
            support_count=2,
        )
        Triple.objects.create(
            subject_label="gamma",
            predicate_label="related_to",
            object_label="delta",
            subject_norm="gamma",
            predicate_norm="related_to",
            object_norm="delta",
            key="gamma|related_to|delta|low",
            confidence=0.3,
            support_count=1,
        )

        response = self.client.get("/api/graph", {"limit": 10, "min_confidence": 0.5})

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.data["meta"]["totalEdges"])
        self.assertEqual(1, response.data["meta"]["returnedEdges"])
        self.assertFalse(response.data["meta"]["limited"])
        self.assertEqual(0.5, response.data["meta"]["minConfidence"])
        self.assertEqual([f"triple-{passing_triple.id}"], [edge["data"]["id"] for edge in response.data["edges"]])

    def test_graph_endpoint_filters_edges_by_document_ids(self):
        first_document = Document.objects.create(
            file=SimpleUploadedFile("first.pdf", b"%PDF-1.4 first", content_type="application/pdf")
        )
        second_document = Document.objects.create(
            file=SimpleUploadedFile("second.pdf", b"%PDF-1.4 second", content_type="application/pdf")
        )
        first_triple = Triple.objects.create(
            subject_label="alpha",
            predicate_label="related_to",
            object_label="beta",
            subject_norm="alpha",
            predicate_norm="related_to",
            object_norm="beta",
            key="alpha|related_to|beta|doc1",
            confidence=0.9,
            support_count=2,
        )
        second_triple = Triple.objects.create(
            subject_label="gamma",
            predicate_label="related_to",
            object_label="delta",
            subject_norm="gamma",
            predicate_norm="related_to",
            object_norm="delta",
            key="gamma|related_to|delta|doc2",
            confidence=0.7,
            support_count=1,
        )
        TripleEvidence.objects.create(triple=first_triple, document=first_document, confidence=0.9)
        TripleEvidence.objects.create(triple=second_triple, document=second_document, confidence=0.7)

        response = self.client.get("/api/graph", {"limit": 10, "document_ids": str(first_document.id)})

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.data["meta"]["totalEdges"])
        self.assertEqual(1, response.data["meta"]["returnedEdges"])
        self.assertEqual([first_document.id], response.data["meta"]["documentIds"])
        self.assertEqual([f"triple-{first_triple.id}"], [edge["data"]["id"] for edge in response.data["edges"]])


class TaskQueueTests(TestCase):
    def test_drain_queue_processes_all_queued_documents_in_order(self):
        first = Document.objects.create(
            file=SimpleUploadedFile("first.pdf", b"%PDF-1.4 first", content_type="application/pdf"),
            status=Document.STATUS_QUEUED,
        )
        second = Document.objects.create(
            file=SimpleUploadedFile("second.pdf", b"%PDF-1.4 second", content_type="application/pdf"),
            status=Document.STATUS_QUEUED,
        )
        third = Document.objects.create(
            file=SimpleUploadedFile("third.pdf", b"%PDF-1.4 third", content_type="application/pdf"),
            status=Document.STATUS_QUEUED,
        )

        processed_ids = []

        def fake_run(document_id):
            processed_ids.append(document_id)
            Document.objects.filter(id=document_id).update(status=Document.STATUS_COMPLETED)

        with patch("kg.tasks._run_document_ingestion", side_effect=fake_run):
            tasks._drain_document_ingestion_queue()

        self.assertEqual([first.id, second.id, third.id], processed_ids)
        self.assertFalse(Document.objects.filter(status=Document.STATUS_QUEUED).exists())
