"""
This file contains the views for the UKG web application (backend).
It defines the views for the API endpoints for the application.
"""
import re

from pathlib import Path
from django.db import connection, transaction
from django.db.models import Exists, OuterRef, Q
from django.conf import settings
from rest_framework import parsers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Document, Reference, Section, SectionCitation, Triple, TripleEvidence
from .serializers import DocumentSerializer, ReferenceSerializer, SectionSerializer
from .tasks import enqueue_document_ingestion
from .utils import edge_opacity

# ================================================
# Helper functions
# ================================================

def citations_for_section(section):
    """
    Returns a list of Reference objects for the citations that occur in a section.
    If a section has citations with index [1, 2, 3], it will return the references for the citations with indices 1, 2, and 3.

    Input:
        section: The section to get the citations for.
    Returns:
        A list of Reference objects for the citations that occur in the section.
    """
    if section is None:
        return []

    citations = (
        SectionCitation.objects.filter(section=section)
        .select_related("reference")
        .order_by("reference__ref_index", "reference__id")
    )

    result = []
    seen_ref_ids = set()
    for citation in citations:
        reference = citation.reference
        # Skip if the reference is None or already seen
        if reference is None or reference.id in seen_ref_ids:
            continue
        seen_ref_ids.add(reference.id)

        # Build the URL for the reference if it is not already set (but the DOI or PMID is set)
        url = reference.url
        if not url and reference.doi:
            url = f"https://doi.org/{reference.doi}"
        elif not url and reference.pmid:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{reference.pmid}/"

        result.append(
            {
                "id": reference.id,
                "ref_index": reference.ref_index,
                "text": reference.text,
                "doi": reference.doi,
                "pmid": reference.pmid,
                "url": url,
                "citations_count": reference.citations_count,
            }
        )
    return result

def parse_document_ids(raw_value):
    """
    Parses a comma-separated list of document IDs from a string.

    Input:
        raw_value: The string to parse the document IDs from.
        Example:
        "1,2,3" -> [1, 2, 3] 
    Returns:
        A list of document IDs.
    """
    if raw_value is None:
        return None

    document_ids = []
    for chunk in raw_value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            document_ids.append(int(chunk))
        except (TypeError, ValueError):
            continue

    return document_ids


class UploadDocumentView(APIView):
    """
    Uploads a document or documents to the application.
    The document(s) are queued for ingestion.
    """
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):

        # Get the list of uploaded files
        upload_files = request.FILES.getlist("files")
        if not upload_files:
            upload_file = request.FILES.get("file")
            if upload_file is not None:
                upload_files = [upload_file]

        # If no files are uploaded, return an error
        if not upload_files:
            return Response(
                {"detail": "Expected file field 'file' or 'files'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure only PDF files are accepted
        invalid_files = [upload_file.name for upload_file in upload_files if not upload_file.name.lower().endswith(".pdf")]
        if invalid_files:
            return Response({"detail": "Only PDF files are supported."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the documents and queue them for ingestion
        with transaction.atomic():
            documents = [
                Document.objects.create(file=upload_file, status=Document.STATUS_QUEUED)
                for upload_file in upload_files
            ]
            transaction.on_commit(lambda: enqueue_document_ingestion())

        return Response(
            {
                "document": DocumentSerializer(documents[0]).data,
                "documents": DocumentSerializer(documents, many=True).data,
                "message": "Upload accepted. Processing queued.",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class DocumentDetailView(APIView):
    """
    Returns the details of a single document, or deletes it along with all
    related data (sections, references, citations, evidence, and any triples
    left without evidence).
    """
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

    def delete(self, request, document_id: int):
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            # Collect triples linked to this document *before* removing evidence.
            affected_triple_ids = set(
                TripleEvidence.objects
                .filter(document=document)
                .values_list("triple_id", flat=True)
            )

            # Remove all evidence, citations, sections, and references that
            # belong to this document. Cascade on Section handles
            # SectionCitation automatically.
            TripleEvidence.objects.filter(document=document).delete()
            document.sections.all().delete()
            document.references.all().delete()

            # Delete any triples that no longer have *any* evidence.
            if affected_triple_ids:
                orphaned = (
                    Triple.objects
                    .filter(id__in=affected_triple_ids)
                    .exclude(
                        id__in=TripleEvidence.objects
                        .filter(triple_id__in=affected_triple_ids)
                        .values("triple_id")
                    )
                )
                orphaned.delete()

            # Clean up the uploaded file from disk.
            if document.file:
                try:
                    document.file.delete(save=False)
                except Exception:
                    pass

            document.delete()

        return Response({"detail": "Document deleted."}, status=status.HTTP_200_OK)


class DocumentListView(APIView):
    """
    Returns a list of all documents (in descending order of creation date).

    Input:
        request: The request object.
    Returns:
        A response object with the list of documents.
    """
    def get(self, request):
        documents = Document.objects.order_by("-created_at")
        return Response(DocumentSerializer(documents, many=True).data)


class GraphView(APIView):
    """
    Retrieves the graph data for the graph view.

    Input:
        request: The request object.
    Returns:
        A response object with the graph data.
    """
    def get(self, request):
        triples = Triple.objects.all()
        q = request.GET.get("q", "").strip()
        document_ids = parse_document_ids(request.GET.get("document_ids"))

        # Get the limit and minimum confidence from the request (default to 1000 if not provided)
        try:
            limit = int(request.GET.get("limit", 1000))
        except (TypeError, ValueError):
            # If limit was provided but not a valid integer, set it to 1000
            limit = 1000

        # Get the minimum threshold confidence from the request (default to 0 if not provided)
        try:
            min_confidence = float(request.GET.get("min_confidence", 0))
        except (TypeError, ValueError):
            min_confidence = 0

        # Ensure the limit and minimum confidence are within valid ranges
        limit = max(1, min(limit, 250000))
        min_confidence = max(0.0, min(min_confidence, 1.0))

        # Filter the triples based on the query
        if q:
            triples = triples.filter(
                Q(subject_label__icontains=q)
                | Q(predicate_label__icontains=q)
                | Q(object_label__icontains=q)
            )
        if document_ids is not None:
            if document_ids:
                # Filter the triple evidence objects based on the document IDs requested
                evidence_exists = TripleEvidence.objects.filter(
                    triple=OuterRef("pk"), document_id__in=document_ids
                )
                triples = triples.filter(Exists(evidence_exists))
            else:
                triples = triples.none()

        # Filter the triples based on the minimum confidence threshold
        triples = triples.filter(confidence__gte=min_confidence)
        # Order the triples by confidence (descending), support count (descending), and ID (ascending)
        triples = triples.order_by("-confidence", "-support_count", "id")
        total_triples = triples.count()

        # Use limit + 1 to check if more data was truncated (saves using another COUNT(*) query on the filtered set)
        rows = list(
            triples.values(
                "id",
                "subject_norm",
                "object_norm",
                "subject_label",
                "object_label",
                "predicate_label",
                "confidence",
                "support_count",
            )[: limit + 1]
        )
        limited = len(rows) > limit

        # If more data was truncated, truncate the rows to the limit
        # This is passed to the frontend that more data is available (than the given limit for the graph)
        if limited:
            rows = rows[:limit]

        # Create a map of the nodes by their normalized subject and object
        nodes_by_id = {}
        # Create a list of the edges
        edges = []

        # Iterate over the rows and create the nodes and edges
        for row in rows:
            subject_norm = row["subject_norm"]
            object_norm = row["object_norm"]
            if not subject_norm or not object_norm:
                continue

            # Create the node for either the subject or object if it is not already in the map
            if subject_norm not in nodes_by_id:
                nodes_by_id[subject_norm] = {
                    "id": subject_norm,
                    "label": row["subject_label"],
                }
            if object_norm not in nodes_by_id:
                nodes_by_id[object_norm] = {
                    "id": object_norm,
                    "label": row["object_label"],
                }
            confidence = row["confidence"]

            # Create the edge for the triple
            edges.append(
                {
                    "id": f"triple-{row['id']}",
                    "source": subject_norm,
                    "target": object_norm,
                    "label": row["predicate_label"],
                    "confidence": confidence,
                    "opacity": edge_opacity(confidence),
                    "supportCount": row["support_count"],
                }
            )

        return Response(
            {
                "nodes": list(nodes_by_id.values()),
                "edges": edges,
                "meta": {
                    "totalEdges": total_triples,
                    "returnedEdges": len(edges),
                    "limited": limited,
                    "documentIds": document_ids if document_ids is not None else None,
                    "minConfidence": min_confidence,
                },
            }
        )


class SearchView(APIView):
    """
    Performs a search on the graph based on the query and type.

    Input:
        request: The request object.
    Returns:
        A response object with the search results.
    """
    def get(self, request):

        # Get the query and type from the request
        query = request.GET.get("q", "").strip()

        # Get the search type from the request
        # - Entity: search for entities
        # - Relation: search for relations
        search_type = request.GET.get("type", "entity").strip().lower()

        # Get the match mode from the request
        # - Contains: search for entities or relations that contain the query anywhere in the text
        # - Word: search for entities or relations that contain the query as a word
        # - Exact: search for entities or relations that match the query exactly
        match_mode = request.GET.get("match_mode", "contains").strip().lower()
        document_ids = parse_document_ids(request.GET.get("document_ids"))

        # Get the limit and minimum confidence from the request (default to 1000 if not provided)
        try:
            limit = int(request.GET.get("limit", 1000))
        except (TypeError, ValueError):
            limit = 1000

        # Get the minimum threshold confidence from the request (default to 0 if not provided)
        try:
            min_confidence = float(request.GET.get("min_confidence", 0))
        except (TypeError, ValueError):
            min_confidence = 0

        # If no query is provided, return an empty response
        if not query:
            return Response(
                {
                    "nodes": [],
                    "edges": [],
                    "matches": [],
                    "highlight": {"nodeIds": [], "edgeIds": []},
                    "meta": {
                        "totalEdges": 0,
                        "returnedEdges": 0,
                        "limited": False,
                        "documentIds": document_ids if document_ids is not None else None,
                        "minConfidence": min_confidence,
                    },
                }
            )

        # Normalize the query by replacing spaces with underscores
        normalized_query = "_".join(query.split())

        # Ensure the limit and minimum confidence are within valid ranges
        limit = max(1, min(limit, 250000))
        min_confidence = max(0.0, min(min_confidence, 1.0))

        if match_mode not in ("contains", "word", "exact"):
            match_mode = "contains"

        # Build the filter Q objects based on the match mode
        triples = Triple.objects.all()
        if match_mode == "exact":
            if search_type == "relation":
                triples = triples.filter(
                    Q(predicate_label__iexact=query)
                    | Q(predicate_label__iexact=normalized_query)
                    | Q(predicate_norm__iexact=query)
                    | Q(predicate_norm__iexact=normalized_query)
                )
            else:
                triples = triples.filter(
                    Q(subject_label__iexact=query)
                    | Q(subject_label__iexact=normalized_query)
                    | Q(object_label__iexact=query)
                    | Q(object_label__iexact=normalized_query)
                    | Q(subject_norm__iexact=query)
                    | Q(subject_norm__iexact=normalized_query)
                    | Q(object_norm__iexact=query)
                    | Q(object_norm__iexact=normalized_query)
                )
        elif match_mode == "word":
            # Create a regular expression pattern to match the query as a word
            escaped = re.escape(normalized_query)
            word_pattern = r"(^|_)" + escaped + r"(_|$)"
            if search_type == "relation":
                triples = triples.filter(
                    Q(predicate_label__iregex=word_pattern)
                    | Q(predicate_norm__iregex=word_pattern)
                )
            else:
                triples = triples.filter(
                    Q(subject_label__iregex=word_pattern)
                    | Q(object_label__iregex=word_pattern)
                    | Q(subject_norm__iregex=word_pattern)
                    | Q(object_norm__iregex=word_pattern)
                )
        else:
            if search_type == "relation":
                triples = triples.filter(
                    Q(predicate_label__icontains=query)
                    | Q(predicate_label__icontains=normalized_query)
                    | Q(predicate_norm__icontains=query)
                    | Q(predicate_norm__icontains=normalized_query)
                )
            else:
                triples = triples.filter(
                    Q(subject_label__icontains=query)
                    | Q(subject_label__icontains=normalized_query)
                    | Q(object_label__icontains=query)
                    | Q(object_label__icontains=normalized_query)
                    | Q(subject_norm__icontains=query)
                    | Q(subject_norm__icontains=normalized_query)
                    | Q(object_norm__icontains=query)
                    | Q(object_norm__icontains=normalized_query)
                )

        if document_ids is not None:
            if document_ids:
                # Filter the triple evidence objects based on the document IDs requested
                evidence_exists = TripleEvidence.objects.filter(
                    triple=OuterRef("pk"), document_id__in=document_ids
                )
                triples = triples.filter(Exists(evidence_exists))
            else:
                triples = triples.none()

        # Filter the triples based on the minimum confidence threshold
        triples = triples.filter(confidence__gte=min_confidence)
        # Order the triples by confidence (descending), support count (descending), and ID (ascending)
        triples = triples.order_by("-confidence", "-support_count", "id")
        total_triples = triples.count()
        triples = list(triples[:limit])
        limited = total_triples > limit

        edge_ids = [f"triple-{item.id}" for item in triples]
        node_ids= set()
        nodes_by_id = {}
        edges = []

        # Iterate over the triples to build the response payload
        for item in triples:
            if item.subject_norm:
                node_ids.add(item.subject_norm)
                if item.subject_norm not in nodes_by_id:
                    nodes_by_id[item.subject_norm] = {
                        "id": item.subject_norm,
                        "label": item.subject_label,
                    }
            if item.object_norm:
                node_ids.add(item.object_norm)
                if item.object_norm not in nodes_by_id:
                    nodes_by_id[item.object_norm] = {
                        "id": item.object_norm,
                        "label": item.object_label,
                    }
            if item.subject_norm and item.object_norm:
                edges.append(
                    {
                        "id": f"triple-{item.id}",
                        "source": item.subject_norm,
                        "target": item.object_norm,
                        "label": item.predicate_label,
                        "confidence": item.confidence,
                        "opacity": edge_opacity(item.confidence),
                        "supportCount": item.support_count,
                    }
                )

        return Response(
            {
                "nodes": list(nodes_by_id.values()),
                "edges": edges,
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
                "meta": {
                    "totalEdges": total_triples,
                    "returnedEdges": len(edges),
                    "limited": limited,
                    "documentIds": document_ids if document_ids is not None else None,
                    "minConfidence": min_confidence,
                },
            }
        )


class TripleDetailView(APIView):
    """
    Return the full details of a single triple including every evidence entry
    with the source document, section path, and the section's citations
    (hyperlinked references with their citation counts).
    """

    def get(self, request, triple_id: int):
        try:
            triple = Triple.objects.get(id=triple_id)
        except Triple.DoesNotExist:
            return Response({"detail": "Triple not found."}, status=status.HTTP_404_NOT_FOUND)

        evidence_qs = (
            TripleEvidence.objects.filter(triple=triple)
            .select_related("document", "section")
            .order_by("-confidence", "-created_at", "id")
        )

        # Create a list of the evidence payload objects
        evidence_payload = []
        for evidence in evidence_qs:
            document = evidence.document
            section = evidence.section
            evidence_payload.append(
                {
                    "id": evidence.id,
                    "confidence": evidence.confidence,
                    "source_method": evidence.source_method,
                    "created_at": evidence.created_at,
                    "document": {
                        "id": document.id if document else None,
                        "title": (document.title or None) if document else None,
                        "file": (document.file.name if document and document.file else None),
                        "doi": document.doi if document else None,
                        "journal": document.journal if document else None,
                        "published_date": document.published_date if document else None,
                        "citations_count": document.citations_count if document else None,
                    }
                    if document else None,
                    "section": {
                        "id": section.id,
                        "heading": section.heading,
                        "path": section.path or section.heading,
                        "level": section.level,
                        "page_numbers": section.page_numbers,
                    }
                    if section else None,
                    "citations": citations_for_section(section),
                }
            )

        return Response(
            {
                "id": triple.id,
                "subject": triple.subject_label,
                "predicate": triple.predicate_label,
                "object": triple.object_label,
                "subject_norm": triple.subject_norm,
                "predicate_norm": triple.predicate_norm,
                "object_norm": triple.object_norm,
                "confidence": triple.confidence,
                "support_count": triple.support_count,
                "last_seen": triple.last_seen,
                "evidence": evidence_payload,
            }
        )


class ClearAllView(APIView):
    """
    Clears all data from the database.

    Input:
        request: The request object.
    Returns:
        A response object with a success message.
    """
    def delete(self, request):
        with transaction.atomic():
            # Delete all the data in the database
            SectionCitation.objects.all().delete()
            TripleEvidence.objects.all().delete()
            Triple.objects.all().delete()
            Reference.objects.all().delete()
            Section.objects.all().delete()
            Document.objects.all().delete()
        
        # Delete all the files in the media/documents/ directory
        media_dir = Path(settings.MEDIA_ROOT)
        documents_dir = media_dir / "documents"
        if documents_dir.exists():
            for document_file in documents_dir.glob("*"):
                try:
                    document_file.unlink()
                except Exception:
                    pass

        return Response({"detail": "All data cleared."}, status=status.HTTP_200_OK)