from django.contrib import admin

from .models import Document, Reference, Section, SectionCitation, Triple, TripleEvidence


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
