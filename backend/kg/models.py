from django.db import models
from django.utils import timezone


class Document(models.Model):
    """
    The Document model represents a PDF file that has been uploaded to the application.
    This class contains the metadata extracted from the PDF file (expected as a scientific article).
    """
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

    file = models.FileField(upload_to="documents/")                                             # The file of the document.
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_QUEUED)     # The status of the document.

    title = models.CharField(max_length=512, blank=True, default="")                            # The title of the document.
    doi = models.CharField(max_length=128, blank=True, null=True)                               # The DOI of the document.
    journal = models.CharField(max_length=255, blank=True, null=True)                           # The journal of the document.
    article_type = models.CharField(max_length=255, blank=True, null=True)                      # The article type of the document.
    received_date = models.CharField(max_length=32, blank=True, null=True)                      # The received date of the document.
    accepted_date = models.CharField(max_length=32, blank=True, null=True)                      # The accepted date of the document.
    published_date = models.CharField(max_length=32, blank=True, null=True)                     # The published date of the document.
    citations_count = models.IntegerField(default=0)                                            # The number of citations found within the document.
    authors = models.JSONField(default=list, blank=True)                                        # The authors of the document.
    metadata_raw = models.JSONField(default=dict, blank=True)                                   # The raw metadata of the document.

    error_message = models.TextField(blank=True, default="")                                    # The error message associated with the document.
    created_at = models.DateTimeField(auto_now_add=True)                                        # The date and time the document was created.
    updated_at = models.DateTimeField(auto_now=True)                                            # The date and time the document was last updated.

    def __str__(self) -> str:
        return self.title or f"Document {self.pk}"


class Section(models.Model):
    """ Represents a section of a document. """
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="sections")   # The document that the section belongs to.
    heading = models.CharField(max_length=255)                                                  # The heading of the section.
    path = models.CharField(max_length=1024, blank=True, default="")                            # The path of the section (e.g Introduction > Background > Methods).
    level = models.IntegerField(default=1)                                                      # The level of the section (e.g 1 for Introduction, 2 for Background, 3 for Methods).
    parent_heading = models.CharField(max_length=255, blank=True, null=True)                    # The parent heading of the section (e.g Introduction for Background).
    text = models.TextField()                                                                   # The text of the section.
    page_numbers = models.JSONField(default=list, blank=True)                                   # The page numbers of the section.
    number_of_citations = models.IntegerField(default=0)                                        # The number of citations found within the section.
    citations_reference_count = models.IntegerField(default=0)                                  # The number of references of the citations found within the section.

    def __str__(self) -> str:
        return f"{self.document_id}:{self.heading}"


class Reference(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="references")     # The document that the reference belongs to.
    ref_index = models.IntegerField(blank=True, null=True)                                          # The index of the reference in the document.
    text = models.TextField()                                                                       # The text of the reference.
    doi = models.CharField(max_length=128, blank=True, null=True)                                   # The DOI of the reference.
    url = models.URLField(blank=True, null=True, max_length=1024)                                   # The URL of the reference.
    pmid = models.CharField(max_length=64, blank=True, null=True)                                   # The PMID of the reference.
    citations_count = models.IntegerField(default=0)                                                # The number of citations found within the reference.

    class Meta:
        indexes = [models.Index(fields=["document", "ref_index"])]

    def __str__(self) -> str:
        return f"{self.document_id}:{self.ref_index}"


class Triple(models.Model):
    subject_label = models.CharField(max_length=255)              # The label of the subject of the triple.
    predicate_label = models.CharField(max_length=255)            # The label of the predicate of the triple.
    object_label = models.CharField(max_length=255)               # The label of the object of the triple.

    subject_norm = models.CharField(max_length=255)               # The normalized subject of the triple.
    predicate_norm = models.CharField(max_length=255)             # The normalized predicate of the triple.
    object_norm = models.CharField(max_length=255)                # The normalized object of the triple.
    key = models.CharField(max_length=1024, unique=True)          # The key of the triple.

    confidence = models.FloatField(default=0.0)                   # The confidence of the triple.
    support_count = models.PositiveIntegerField(default=0)        # The number of times the triple has been seen.
    last_seen = models.DateTimeField(default=timezone.now)        # The date and time the triple was last seen.

    class Meta:
        indexes = [
            models.Index(fields=["subject_norm"]),
            models.Index(fields=["predicate_norm"]),
            models.Index(fields=["object_norm"]),
        ]

    def __str__(self) -> str:
        return f"({self.subject_label}, {self.predicate_label}, {self.object_label})"


class TripleEvidence(models.Model):
    triple = models.ForeignKey(Triple, on_delete=models.CASCADE, related_name="evidence")                                        # The triple asssociated with this evidence.
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="triple_evidence")                             # The document that the triple belongs to.
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name="triple_evidence")       # The section that the triple belongs to.
    confidence = models.FloatField(default=0.0)                                                                                  # The confidence of the triple.
    source_method = models.CharField(max_length=64, blank=True, default="")                                                      # The method that generated the triple (e.g. "svo", "span").
    created_at = models.DateTimeField(auto_now_add=True)                                                                         # The date and time the triple evidence was created.

    class Meta:
        indexes = [models.Index(fields=["document", "triple"])]


class SectionCitation(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="citations")                                     # The section that the citation belongs to.
    reference = models.ForeignKey(Reference, on_delete=models.CASCADE, related_name="section_mentions")                          # The reference associated with the citation.

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["section", "reference"], name="unique_section_reference_citation"),
        ]
