from __future__ import annotations

import sys
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Document, Reference, Section, SectionCitation, Triple, TripleEvidence
from .utils import normalize_term, triple_key


class PipelineImportError(RuntimeError):
    pass


class ExtractionPipelineService:
    """
    Wraps legacy extraction and triple-generation modules for Django use.
    """

    def __init__(self, src_dir: Path | None = None):
        self.src_dir = Path(src_dir or settings.UKG_SRC_DIR)

    def _ensure_src_in_path(self) -> None:
        src_text = str(self.src_dir)
        if src_text not in sys.path:
            sys.path.insert(0, src_text)

    def _import_pipeline_modules(self):
        self._ensure_src_in_path()
        try:
            from extraction_module import extract_json_data, post_process_json_data
            from generate_triples import generate_triples
        except ModuleNotFoundError as exc:
            raise PipelineImportError("Could not import legacy pipeline modules from src/") from exc
        return extract_json_data, post_process_json_data, generate_triples

    @transaction.atomic
    def process_document(self, document: Document) -> dict[str, int]:
        """
        Processes a document by extracting the JSON data, post-processing the data, and generating triples.
        Input:
            document: The document to process.
        Returns:
            A dictionary containing the number of sections, references, and triples.
        """
        extract_json_data, post_process_json_data, generate_triples = self._import_pipeline_modules()
        document.status = Document.STATUS_PROCESSING
        document.error_message = ""
        document.save(update_fields=["status", "error_message", "updated_at"])

        json_path = extract_json_data(document.file.path)
        if json_path is None:
            raise RuntimeError("PDF extraction returned no JSON output.")

        extraction_result = post_process_json_data(str(json_path), enrich_metadata=True, enrich_references=True)

        document.title = extraction_result.metadata.title or document.title
        document.doi = extraction_result.metadata.doi
        document.journal = extraction_result.metadata.journal
        document.article_type = extraction_result.metadata.article_type
        document.received_date = extraction_result.metadata.received_date
        document.accepted_date = extraction_result.metadata.accepted_date
        document.published_date = extraction_result.metadata.published_date

        # Set the citations count for the document.
        if extraction_result.metadata.citations_count is not None:
            document.citations_count = extraction_result.metadata.citations_count
        else:
            document.citations_count = 0
        
        document.authors = extraction_result.metadata.authors
        document.metadata_raw = extraction_result.metadata.raw
        document.save()

        section_map: dict[str, Section] = {}
        for sec in extraction_result.sections:
            section_obj = Section.objects.create(
                document=document,
                heading=sec.heading,
                path=str(sec.path) if sec.path else sec.heading,
                level=sec.level,
                parent_heading=sec.parent_heading,
                text=sec.text,
                page_numbers=sec.page_numbers,
            )
            section_map[sec.heading] = section_obj

        references_by_index: dict[int, Reference] = {}
        for ref in extraction_result.references:
            if ref.citations_count is not None:
                citations_count = ref.citations_count
            else:
                citations_count = 0
            reference_obj = Reference.objects.create(
                document=document,
                ref_index=ref.index,
                text=ref.text,
                doi=ref.doi,
                url=ref.url,
                pmid=ref.pmid,
                citations_count=citations_count,
            )
            if ref.index is not None:
                references_by_index[int(ref.index)] = reference_obj

        for sec in extraction_result.sections:
            section_obj = section_map.get(sec.heading)
            if not section_obj or not sec.citations:
                continue
            for citation_index in sec.citations:
                ref_obj = references_by_index.get(int(citation_index))
                if ref_obj:
                    SectionCitation.objects.get_or_create(section=section_obj, reference=ref_obj)

        triples = generate_triples(
            extraction_result.sections,
            model_name="en_core_web_lg",
            use_span_extraction=True,
        )
        for triple in triples:
            self.upsert_triple(triple=triple, document=document, section_map=section_map)

        document.status = Document.STATUS_COMPLETED
        document.save(update_fields=["status", "updated_at"])
        return {
            "sections": len(extraction_result.sections),
            "references": len(extraction_result.references),
            "triples": len(triples),
        }

    def upsert_triple(self, triple, document: Document, section_map: dict[str, Section]) -> Triple | None:
        sub_norm = normalize_term(triple.sub)
        pred_norm = normalize_term(triple.pred)
        obj_norm = normalize_term(triple.obj)
        if not sub_norm or not pred_norm or not obj_norm:
            return None
        key = triple_key(sub_norm, pred_norm, obj_norm)

        # Get the section object for the triple.
        section_obj = section_map.get(triple.section or "")
        if section_obj:
            # Count the number of citations and the citations reference count for the section.
            section_number_of_citations = section_obj.number_of_citations
            section_citations_reference_count = section_obj.citations_reference_count
        else:
            section_number_of_citations = 0
            section_citations_reference_count = 0
        
        # Calculate the confidence value boost based on the number of citations (of the source document) and the citations reference count (of the source section).
        document_citations_count = document.citations_count
        if section_number_of_citations == 0:
            section_citation_average = 0
        else:
            section_citation_average = section_citations_reference_count / section_number_of_citations

        # For example, if the section citation average is 1000, the boost will be 0.05.
        section_boost = max(0.1, section_citation_average / 20000)
        # For example, if the document citations count is 1000, the boost will be 0.1.
        document_boost = max(0.2, document_citations_count / 10000)
        total_boost = section_boost + document_boost

        # Calculate the confidence for the triple.
        confidence = max(0.0, min(1.0, float(triple.conf) + total_boost))

        # Upsert the triple.
        triple_obj, created = Triple.objects.get_or_create(
            key=key,
            defaults={
                "subject_label": triple.sub,
                "predicate_label": triple.pred,
                "object_label": triple.obj,
                "subject_norm": sub_norm,
                "predicate_norm": pred_norm,
                "object_norm": obj_norm,
                "confidence": confidence,
                "support_count": 1,
                "last_seen": timezone.now(),
            },
        )

        if not created:
            triple_obj.confidence = min(1.0, (triple_obj.confidence * 0.7 + confidence * 0.3) + 0.01)
            triple_obj.support_count += 1
            triple_obj.last_seen = timezone.now()
            triple_obj.save(update_fields=["confidence", "support_count", "last_seen"])


        TripleEvidence.objects.create(
            triple=triple_obj,
            document=document,
            section=section_obj,
            confidence=confidence,
            source_method=(triple.source or "")[:64],
        )
        return triple_obj
