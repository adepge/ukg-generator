from rest_framework import serializers

from .models import Document, Reference, Section, Triple, TripleEvidence


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id",
            "file",
            "status",
            "title",
            "doi",
            "journal",
            "article_type",
            "received_date",
            "accepted_date",
            "published_date",
            "citations_count",
            "authors",
            "metadata_raw",
            "error_message",
            "created_at",
            "updated_at",
        ]


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = [
            "id",
            "heading",
            "path",
            "level",
            "parent_heading",
            "text",
            "page_numbers",
            "number_of_citations",
            "citations_reference_count",
        ]


class ReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reference
        fields = ["id", "ref_index", "text", "doi", "url", "pmid", "citations_count"]


class TripleEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripleEvidence
        fields = ["id", "document", "section", "confidence", "source_method", "created_at"]


class TripleSerializer(serializers.ModelSerializer):
    evidence = TripleEvidenceSerializer(many=True, read_only=True)

    class Meta:
        model = Triple
        fields = [
            "id",
            "subject_label",
            "predicate_label",
            "object_label",
            "subject_norm",
            "predicate_norm",
            "object_norm",
            "key",
            "confidence",
            "support_count",
            "last_seen",
            "evidence",
        ]
