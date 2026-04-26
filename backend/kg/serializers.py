"""
The file contains the serializers for all models in the application.
"""

from rest_framework import serializers
from .models import (
    Blacklist,
    BlacklistTerm,
    Document,
    EntityLabel,
    LabelList,
    Ontology,
    Reference,
    RelationLabel,
    Section,
    Triple,
    TripleEvidence,
)


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


# ================================================
# Settings serializers
# ================================================


class BlacklistTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlacklistTerm
        fields = [
            "id",
            "term",
            "category",
            "exact_match",
            "subject",
            "object",
            "default_exact_match",
            "default_subject",
            "default_object",
        ]
        read_only_fields = [
            "id",
            "term",
            "category",
            "default_exact_match",
            "default_subject",
            "default_object",
        ]


class BlacklistSerializer(serializers.ModelSerializer):
    term_count = serializers.SerializerMethodField()

    class Meta:
        model = Blacklist
        fields = [
            "id",
            "name",
            "source",
            "is_default",
            "is_enabled",
            "term_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_term_count(self, obj: Blacklist) -> int:
        return obj.terms.count()


class EntityLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityLabel
        fields = ["id", "label", "description", "order"]


class RelationLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelationLabel
        fields = ["id", "label", "order"]


class LabelListSerializer(serializers.ModelSerializer):
    entity_label_count = serializers.SerializerMethodField()
    relation_label_count = serializers.SerializerMethodField()

    class Meta:
        model = LabelList
        fields = [
            "id",
            "name",
            "source",
            "is_active",
            "entity_label_count",
            "relation_label_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_entity_label_count(self, obj: LabelList) -> int:
        return obj.entity_labels.count()

    def get_relation_label_count(self, obj: LabelList) -> int:
        return obj.relation_labels.count()


class LabelListDetailSerializer(LabelListSerializer):
    entity_labels = EntityLabelSerializer(many=True, read_only=True)
    relation_labels = RelationLabelSerializer(many=True, read_only=True)

    class Meta(LabelListSerializer.Meta):
        fields = LabelListSerializer.Meta.fields + ["entity_labels", "relation_labels"]
        read_only_fields = fields


class OntologySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ontology
        fields = [
            "id",
            "name",
            "source",
            "is_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
