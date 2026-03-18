from django.db import models
from django.utils import timezone


class Document(models.Model):
    STATUS_QUEUED = "queued"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    file = models.FileField(upload_to="documents/")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_QUEUED)

    title = models.CharField(max_length=512, blank=True, default="")
    doi = models.CharField(max_length=128, blank=True, null=True)
    journal = models.CharField(max_length=255, blank=True, null=True)
    article_type = models.CharField(max_length=255, blank=True, null=True)
    received_date = models.CharField(max_length=32, blank=True, null=True)
    accepted_date = models.CharField(max_length=32, blank=True, null=True)
    published_date = models.CharField(max_length=32, blank=True, null=True)
    citations_count = models.IntegerField(default=0)
    authors = models.JSONField(default=list, blank=True)
    metadata_raw = models.JSONField(default=dict, blank=True)

    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title or f"Document {self.pk}"


class Section(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="sections")
    heading = models.CharField(max_length=255)
    path = models.CharField(max_length=1024, blank=True, default="")
    level = models.IntegerField(default=1)
    parent_heading = models.CharField(max_length=255, blank=True, null=True)
    text = models.TextField()
    page_numbers = models.JSONField(default=list, blank=True)

    def __str__(self) -> str:
        return f"{self.document_id}:{self.heading}"


class Reference(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="references")
    ref_index = models.IntegerField(blank=True, null=True)
    text = models.TextField()
    doi = models.CharField(max_length=128, blank=True, null=True)
    url = models.URLField(blank=True, null=True, max_length=1024)
    pmid = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["document", "ref_index"])]

    def __str__(self) -> str:
        return f"{self.document_id}:{self.ref_index}"


class Triple(models.Model):
    subject_label = models.CharField(max_length=255)
    predicate_label = models.CharField(max_length=255)
    object_label = models.CharField(max_length=255)

    subject_norm = models.CharField(max_length=255)
    predicate_norm = models.CharField(max_length=255)
    object_norm = models.CharField(max_length=255)
    key = models.CharField(max_length=1024, unique=True)

    confidence = models.FloatField(default=0.0)
    support_count = models.PositiveIntegerField(default=0)
    last_seen = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["subject_norm"]),
            models.Index(fields=["predicate_norm"]),
            models.Index(fields=["object_norm"]),
        ]

    def __str__(self) -> str:
        return f"({self.subject_label}, {self.predicate_label}, {self.object_label})"


class TripleEvidence(models.Model):
    triple = models.ForeignKey(Triple, on_delete=models.CASCADE, related_name="evidence")
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="triple_evidence")
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name="triple_evidence")
    confidence = models.FloatField(default=0.0)
    source_method = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["document", "triple"])]


class SectionCitation(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="citations")
    reference = models.ForeignKey(Reference, on_delete=models.CASCADE, related_name="section_mentions")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["section", "reference"], name="unique_section_reference_citation"),
        ]
