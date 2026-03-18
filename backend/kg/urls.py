from django.urls import path

from .views import (
    DocumentDetailView,
    DocumentListView,
    GraphView,
    SearchView,
    UploadDocumentView,
)


urlpatterns = [
    path("documents/upload", UploadDocumentView.as_view(), name="document-upload"),
    path("documents", DocumentListView.as_view(), name="document-list"),
    path("documents/<int:document_id>", DocumentDetailView.as_view(), name="document-detail"),
    path("graph", GraphView.as_view(), name="graph"),
    path("search", SearchView.as_view(), name="search"),
]
