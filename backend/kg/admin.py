"""
Admin configuration for the Knowledge Graph application.
This registers the models with the admin site (localhost:8000/admin) and provides a basic interface for managing the data.
"""

from django.contrib import admin
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
    SectionCitation,
    Triple,
    TripleEvidence,
)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "doi", "status", "created_at")
    search_fields = ("title", "doi")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("id", "document_id", "heading", "level")
    search_fields = ("heading", "path")


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    list_display = ("id", "document_id", "ref_index", "doi")
    search_fields = ("text", "doi", "pmid")


@admin.register(Triple)
class TripleAdmin(admin.ModelAdmin):
    list_display = ("id", "subject_label", "predicate_label", "object_label", "confidence", "support_count")
    search_fields = ("subject_label", "predicate_label", "object_label")


@admin.register(TripleEvidence)
class TripleEvidenceAdmin(admin.ModelAdmin):
    list_display = ("id", "triple_id", "document_id", "section_id", "confidence", "source_method")


@admin.register(SectionCitation)
class SectionCitationAdmin(admin.ModelAdmin):
    list_display = ("id", "section_id", "reference_id")


@admin.register(Blacklist)
class BlacklistAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "source", "is_default", "is_enabled", "updated_at")
    list_filter = ("source", "is_default", "is_enabled")
    search_fields = ("name",)


@admin.register(BlacklistTerm)
class BlacklistTermAdmin(admin.ModelAdmin):
    list_display = ("id", "blacklist_id", "term", "category", "exact_match", "subject", "object")
    list_filter = ("blacklist", "exact_match", "category")
    search_fields = ("term", "category")


@admin.register(LabelList)
class LabelListAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "source", "is_active", "updated_at")
    list_filter = ("source", "is_active")
    search_fields = ("name",)


@admin.register(EntityLabel)
class EntityLabelAdmin(admin.ModelAdmin):
    list_display = ("id", "label_list_id", "label", "order")
    search_fields = ("label",)


@admin.register(RelationLabel)
class RelationLabelAdmin(admin.ModelAdmin):
    list_display = ("id", "label_list_id", "label", "order")
    search_fields = ("label",)


@admin.register(Ontology)
class OntologyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "source", "is_enabled", "updated_at")
    list_filter = ("source", "is_enabled")
    search_fields = ("name",)
