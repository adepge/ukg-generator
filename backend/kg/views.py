from django.db.models import Q
from rest_framework import parsers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, Triple
from .serializers import DocumentSerializer, ReferenceSerializer, SectionSerializer
from .tasks import enqueue_document_ingestion
from .utils import edge_opacity


class UploadDocumentView(APIView):
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        upload_file = request.FILES.get("file")
        if upload_file is None:
            return Response({"detail": "Expected file field 'file'."}, status=status.HTTP_400_BAD_REQUEST)
        if not upload_file.name.lower().endswith(".pdf"):
            return Response({"detail": "Only PDF files are supported."}, status=status.HTTP_400_BAD_REQUEST)

        document = Document.objects.create(file=upload_file, status=Document.STATUS_QUEUED)
        enqueue_document_ingestion(document.id)
        return Response(
            {
                "document": DocumentSerializer(document).data,
                "message": "Upload accepted. Processing started.",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class DocumentDetailView(APIView):
    def get(self, request, document_id: int):
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "document": DocumentSerializer(document).data,
                "sections": SectionSerializer(document.sections.all(), many=True).data,
                "references": ReferenceSerializer(document.references.all(), many=True).data,
            }
        )


class DocumentListView(APIView):
    def get(self, request):
        documents = Document.objects.order_by("-created_at")
        return Response(DocumentSerializer(documents, many=True).data)


class GraphView(APIView):
    def get(self, request):
        triples = Triple.objects.all()
        q = request.GET.get("q", "").strip()
        if q:
            triples = triples.filter(
                Q(subject_label__icontains=q)
                | Q(predicate_label__icontains=q)
                | Q(object_label__icontains=q)
            )

        nodes_by_id: dict[str, dict] = {}
        edges: list[dict] = []
        for triple in triples:
            if not triple.subject_norm or not triple.object_norm:
                continue
            nodes_by_id.setdefault(
                triple.subject_norm,
                {"data": {"id": triple.subject_norm, "label": triple.subject_label}},
            )
            nodes_by_id.setdefault(
                triple.object_norm,
                {"data": {"id": triple.object_norm, "label": triple.object_label}},
            )
            edges.append(
                {
                    "data": {
                        "id": f"triple-{triple.id}",
                        "source": triple.subject_norm,
                        "target": triple.object_norm,
                        "label": triple.predicate_label,
                        "confidence": triple.confidence,
                        "opacity": edge_opacity(triple.confidence),
                        "supportCount": triple.support_count,
                    }
                }
            )

        return Response({"nodes": list(nodes_by_id.values()), "edges": edges})


class SearchView(APIView):
    def get(self, request):
        query = request.GET.get("q", "").strip()
        search_type = request.GET.get("type", "entity").strip().lower()
        if not query:
            return Response({"matches": [], "highlight": {"nodeIds": [], "edgeIds": []}})

        if search_type == "relation":
            triples = Triple.objects.filter(
                Q(predicate_label__icontains=query) | Q(predicate_norm__icontains=query)
            )
        else:
            triples = Triple.objects.filter(
                Q(subject_label__icontains=query)
                | Q(object_label__icontains=query)
                | Q(subject_norm__icontains=query)
                | Q(object_norm__icontains=query)
            )

        edge_ids = [f"triple-{item.id}" for item in triples]
        node_ids: set[str] = set()
        for item in triples:
            if item.subject_norm:
                node_ids.add(item.subject_norm)
            if item.object_norm:
                node_ids.add(item.object_norm)

        return Response(
            {
                "matches": [
                    {
                        "id": item.id,
                        "subject": item.subject_label,
                        "predicate": item.predicate_label,
                        "object": item.object_label,
                        "confidence": item.confidence,
                    }
                    for item in triples
                ],
                "highlight": {
                    "nodeIds": sorted(node_ids),
                    "edgeIds": edge_ids,
                },
            }
        )
