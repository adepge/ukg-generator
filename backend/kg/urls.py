"""
This file contains the URL patterns for the UKG web application (backend).
It defines the URL patterns for the API endpoints for the application.
"""

from django.urls import path
from .settings_views import (
    BlacklistDetailView,
    BlacklistDownloadView,
    BlacklistListView,
    BlacklistResetView,
    BlacklistTermDetailView,
    BlacklistTermsView,
    BlacklistToggleView,
    BlacklistUploadView,
    EntityLabelDetailView,
    EntityLabelListView,
    LabelListActivateView,
    LabelListDetailView,
    LabelListListView,
    LabelListResetView,
    OntologyDetailView,
    OntologyListView,
    OntologyUploadView,
    RelationLabelDetailView,
    RelationLabelListView,
    SettingsSummaryView,
)
from .views import (
    ClearAllView,
    DocumentDetailView,
    DocumentListView,
    GraphView,
    SearchView,
    TripleDetailView,
    UploadDocumentView,
)


urlpatterns = [
    # Main API endpoints
    path("documents/upload", UploadDocumentView.as_view(), name="document-upload"),
    path("documents", DocumentListView.as_view(), name="document-list"),
    path("documents/<int:document_id>", DocumentDetailView.as_view(), name="document-detail"),
    path("graph", GraphView.as_view(), name="graph"),
    path("search", SearchView.as_view(), name="search"),
    path("triples/<int:triple_id>", TripleDetailView.as_view(), name="triple-detail"),
    path("clear-all", ClearAllView.as_view(), name="clear-all"),

    # Settings: summary
    path("settings/summary", SettingsSummaryView.as_view(), name="settings-summary"),

    # Settings: blacklists
    path("settings/blacklists", BlacklistListView.as_view(), name="settings-blacklists"),
    path("settings/blacklists/upload", BlacklistUploadView.as_view(), name="settings-blacklist-upload"),
    path("settings/blacklists/<int:blacklist_id>", BlacklistDetailView.as_view(), name="settings-blacklist-detail"),
    path("settings/blacklists/<int:blacklist_id>/terms", BlacklistTermsView.as_view(), name="settings-blacklist-terms"),
    path("settings/blacklists/<int:blacklist_id>/terms/<int:term_id>", BlacklistTermDetailView.as_view(), name="settings-blacklist-term-detail"),
    path("settings/blacklists/<int:blacklist_id>/reset", BlacklistResetView.as_view(), name="settings-blacklist-reset"),
    path("settings/blacklists/<int:blacklist_id>/toggle", BlacklistToggleView.as_view(), name="settings-blacklist-toggle"),
    path("settings/blacklists/<int:blacklist_id>/download", BlacklistDownloadView.as_view(), name="settings-blacklist-download"),

    # Settings: label lists
    path("settings/label-lists", LabelListListView.as_view(), name="settings-label-lists"),
    path("settings/label-lists/<int:label_list_id>", LabelListDetailView.as_view(), name="settings-label-list-detail"),
    path("settings/label-lists/<int:label_list_id>/activate", LabelListActivateView.as_view(), name="settings-label-list-activate"),
    path("settings/label-lists/<int:label_list_id>/reset", LabelListResetView.as_view(), name="settings-label-list-reset"),
    path("settings/label-lists/<int:label_list_id>/entity-labels", EntityLabelListView.as_view(), name="settings-entity-labels"),
    path("settings/label-lists/<int:label_list_id>/entity-labels/<int:entity_id>", EntityLabelDetailView.as_view(), name="settings-entity-label-detail"),
    path("settings/label-lists/<int:label_list_id>/relation-labels", RelationLabelListView.as_view(), name="settings-relation-labels"),
    path("settings/label-lists/<int:label_list_id>/relation-labels/<int:relation_id>", RelationLabelDetailView.as_view(), name="settings-relation-label-detail"),

    # Settings: ontologies
    path("settings/ontologies", OntologyListView.as_view(), name="settings-ontologies"),
    path("settings/ontologies/upload", OntologyUploadView.as_view(), name="settings-ontology-upload"),
    path("settings/ontologies/<int:ontology_id>", OntologyDetailView.as_view(), name="settings-ontology-detail"),
]
