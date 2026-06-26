"""
The file contains the services (containing all the pipeline modules) for creating the knowledge graph from 
the processed documents (PDFs).
"""

import logging
import os
import sys
from pathlib import Path
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import (
    Blacklist,
    Document,
    LabelList,
    Ontology,
    Reference,
    Section,
    SectionCitation,
    Triple,
    TripleEvidence,
)
from .utils import normalize_term, triple_key


logger = logging.getLogger(__name__)


class PipelineImportError(RuntimeError):
    """
    Exception raised when the pipeline modules cannot be imported.
    """
    pass


class ExtractionPipelineService:
    """
    Wrapper for KG generation pipeline (PDF extraction, post-processing, triple generation).
    """
    def __init__(self, src_dir: Path | None = None):
        self.src_dir = Path(src_dir or settings.UKG_SRC_DIR)
    
    def import_pipeline_modules(self):
        """
        Import the pipeline modules from the src directory.
        """
        src_text = str(self.src_dir)
        if src_text not in sys.path:
            sys.path.insert(0, src_text)

        # Check if the pipeline modules are imported successfully
        try:
            from extraction_module import extract_json_data, post_process_json_data
            from generate_triples import generate_triples, build_blacklist_sets
        except ModuleNotFoundError as exc:
            raise PipelineImportError("Could not import legacy pipeline modules from src/") from exc
        return extract_json_data, post_process_json_data, generate_triples, build_blacklist_sets

    def import_evaluation_module(self):
        """
        Import the LLM-as-judge evaluation helpers from the src directory.
        """
        src_text = str(self.src_dir)
        if src_text not in sys.path:
            sys.path.insert(0, src_text)

        try:
            from evaluation import evaluate_triples, write_report_json
        except ModuleNotFoundError as exc:
            raise PipelineImportError("Could not import evaluation module from src/") from exc
        return evaluate_triples, write_report_json

    @staticmethod
    def build_db_blacklist_sets(build_blacklist_sets):
        """
        Build the blacklist sets from every currently-enabled Blacklist row
        (terms materialised into the tuple format build_blacklist_sets expects).

        Input:
            build_blacklist_sets: The function to build the blacklist sets
        Returns:
            A tuple of lists, each containing the blacklisted terms for the subject and object
        """
        enabled_blacklists = Blacklist.objects.filter(
            is_enabled=True
        ).prefetch_related("terms")
        raw_blacklists = []
        for bl in enabled_blacklists:
            # Convert the blacklist terms to a tuple of (term, category, exact_match, subject, object)
            raw_blacklists.append(
                frozenset(
                    (
                        term.term,
                        term.category,
                        "excl_only" if term.exact_match else "excl",
                        "1" if term.subject else "0",
                        "1" if term.object else "0",
                    )
                    for term in bl.terms.all()
                )
            )
        return build_blacklist_sets(raw_blacklists)

    @staticmethod
    def db_ontology_files() -> list[str]:
        """
        Return the filesystem paths of every enabled ontology.
        """
        paths: list[str] = []
        for ontology in Ontology.objects.filter(is_enabled=True):
            resolved = ontology.resolved_path()
            if resolved:
                paths.append(resolved)
        return paths

    @staticmethod
    def db_active_label_list():
        """
        Return (entity_labels, relation_labels) for the currently-active label
        list, or (None, None) to let the extractor fall back to its defaults.
        """
        active = (
            LabelList.objects.filter(is_active=True)
            .prefetch_related("entity_labels", "relation_labels")
            .first()
        )
        if active is None:
            return None, None

        entity_labels = {
            el.label: el.description
            for el in active.entity_labels.all()
        }
        relation_labels = [rl.label for rl in active.relation_labels.all()]
        return (entity_labels or None), (relation_labels or None)

    def process_document(self, document: Document) -> dict[str, int]:
        """
        Process a document end-to-end (PDF extraction, post-processing, triple generation).

        Args:
            document: The document to process
        Returns:
            A dictionary containing the number of sections, references, and triples
        Raises:
            RuntimeError: If the PDF extraction returns no data
        """
        # Import the pipeline modules
        extract_json_data, post_process_json_data, generate_triples, build_blacklist_sets = self.import_pipeline_modules()

        # Load the blacklist/ontology/label configuration from the settings DB
        blacklist_sets = self.build_db_blacklist_sets(build_blacklist_sets)
        ontology_files = self.db_ontology_files()
        entity_labels, relation_labels = self.db_active_label_list()

        # Update the document status to processing
        document.status = Document.STATUS_PROCESSING
        document.error_message = ""
        document.save(update_fields=["status", "error_message", "updated_at"])

        # Extract the JSON data from the PDF
        json_path, pdf_data = extract_json_data(document.file.path, write_json=False)
        if pdf_data is None:
            raise RuntimeError("PDF extraction returned no data.")

        # Post-process the JSON data and enrich the metadata and references
        extraction_result = post_process_json_data(
            json_path=str(json_path) if json_path else None,
            data=pdf_data,
            enrich_metadata=True,
            enrich_references=True,
            output_basename=Path(document.file.name).stem,
        )

        # Generate triples from the sections
        triples = generate_triples(
            extraction_result.sections,
            model_name="en_core_web_lg",
            use_span_extraction=True,
            blacklist_sets=blacklist_sets,
            ontology_files=ontology_files,
            entity_labels=entity_labels,
            relation_labels=relation_labels,
        )

        # Score triples with the LLM-as-judge and drop low-quality ones
        triples = self.evaluate_and_filter_triples(
            triples,
            entity_labels=entity_labels,
            relation_labels=relation_labels,
            document=document,
        )

        # Persist the extraction result and emitted triples atomically
        with transaction.atomic():
            return self.persist_extraction(
                document=document,
                extraction_result=extraction_result,
                triples=triples,
            )

    def evaluate_and_filter_triples(
        self,
        triples,
        entity_labels,
        relation_labels,
        document: Document | None = None,
    ):
        """
        Score triples with the LLM-as-judge and keep only those whose mean
        normalized score (0-1, averaged across all dimensions) is at least
        ``settings.UKG_JUDGE_MIN_SCORE``.

        The step is skipped (all triples kept) when evaluation is disabled, when
        there are no triples, or when no API key is configured. Any evaluation
        error also fails open (keeps all triples) so a transient outage never
        discards an entire document's triples. Triples the judge could not score
        are likewise kept.

        When ``document`` is supplied, the full evaluation report (aggregates and
        per-triple scores) is written to disk under ``settings.UKG_EVAL_REPORT_DIR``.

        Args:
            triples: The pipeline Triple objects to evaluate.
            entity_labels: Active entity labels (domain schema for the judge).
            relation_labels: Active relation labels (domain schema for the judge).
            document: The document being processed (used to name the report file).
        Returns:
            The filtered list of triples.
        """
        if not triples:
            return triples
        if not getattr(settings, "UKG_JUDGE_EVALUATION_ENABLED", True):
            return triples

        try:
            evaluate_triples, write_report_json = self.import_evaluation_module()
        except PipelineImportError as exc:
            logger.warning("Skipping LLM-as-judge evaluation: %s", exc)
            return triples

        # Environment is loaded in the Django settings file
        if not os.environ.get("OPENAI_API_KEY"):
            logger.warning(
                "LLM-as-judge evaluation enabled but OPENAI_API_KEY is not set; "
                "keeping all %d triples.", len(triples),
            )
            return triples

        threshold = float(getattr(settings, "UKG_JUDGE_MIN_SCORE", 0.5))
        try:
            report = evaluate_triples(
                triples,
                entity_labels=entity_labels,
                relation_labels=relation_labels,
            )
        except Exception as exc:
            # Keep all triples if the evaluation fails.
            logger.exception(
                "LLM-as-judge evaluation failed; keeping all %d triples. (%s)",
                len(triples), exc,
            )
            return triples

        # Persist the full report to disk (best-effort; never blocks ingestion).
        if document is not None:
            self.save_evaluation_report(write_report_json, report, document)

        kept = []
        dropped = 0
        unscored = 0
        # Evaluate the triples in the order they were generated.
        for original, evaluation in zip(triples, report.evaluations):
            if evaluation.normalized is None:
                unscored += 1
                kept.append(original)
                continue
            if evaluation.normalized >= threshold:
                kept.append(original)
            else:
                dropped += 1

        logger.info(
            "LLM-as-judge (%s): kept %d/%d triples "
            "(dropped %d below %.2f; %d unscored kept).",
            report.model, len(kept), len(triples), dropped, threshold, unscored,
        )
        return kept

    @staticmethod
    def save_evaluation_report(write_report_json, report, document: Document) -> None:
        """
        Write the LLM-as-judge report for a document to disk as JSON.

        The file is saved under ``settings.UKG_EVAL_REPORT_DIR`` and named after
        the document (its source filename stem and primary key).
        Failures are logged but not raised.

        Args:
            write_report_json: The evaluation module's JSON writer.
            report: The EvaluationReport to persist.
            document: The document the report belongs to.
        """
        try:
            report_dir = Path(getattr(settings, "UKG_EVAL_REPORT_DIR"))
            report_dir.mkdir(parents=True, exist_ok=True)
            stem = Path(document.file.name).stem if document.file else "document"
            output_path = report_dir / f"{stem}_{document.id}.eval.json"
            write_report_json(report, output_path)
            logger.info("Saved LLM-as-judge report to %s", output_path)
        except Exception as exc:
            logger.warning(
                "Could not save LLM-as-judge report for document %s: %s",
                document.id, exc,
            )

    def persist_extraction(
        self,
        document: Document,
        extraction_result,
        triples,
    ) -> dict[str, int]:
        """
        Bulk-persist the extraction result and generated triples.

        Args:
            document: The Document object to save the extraction result and triples for
            extraction_result: The extraction result data to process
            triples: The list of Triple objects to save
        Returns:
            A dictionary containing the number of sections, references, and triples saved
        """
        metadata = extraction_result.metadata
        document.title = metadata.title or document.title
        document.doi = metadata.doi
        document.journal = metadata.journal
        document.article_type = metadata.article_type
        document.received_date = metadata.received_date
        document.accepted_date = metadata.accepted_date
        document.published_date = metadata.published_date
        document.citations_count = metadata.citations_count or 0
        document.authors = metadata.authors
        document.metadata_raw = metadata.raw
        document.save()

        # Bulk-create all sections for this document in a single round-trip.
        section_objs = [
            Section(
                document=document,
                heading=sec.heading,
                path=str(sec.path) if sec.path else sec.heading,
                level=sec.level,
                parent_heading=sec.parent_heading,
                text=sec.text,
                page_numbers=sec.page_numbers,
                number_of_citations=sec.number_of_citations,
                citations_reference_count=sec.citations_reference_count,
            )
            for sec in extraction_result.sections
        ]
        Section.objects.bulk_create(section_objs)

        created_sections = list(
            Section.objects.filter(document=document).order_by("id")
        )

        # Create a map of the sections by heading (this maps the section heading to the corresponding Section object)
        section_map = {}
        for sec, section_obj in zip(extraction_result.sections, created_sections):
            section_map[sec.heading] = section_obj

        # Bulk-create references
        reference_objs = [
            Reference(
                document=document,
                ref_index=ref.index,
                text=ref.text,
                doi=ref.doi,
                url=ref.url,
                pmid=ref.pmid,
                citations_count=ref.citations_count or 0,
            )
            for ref in extraction_result.references
        ]
        if reference_objs:
            Reference.objects.bulk_create(reference_objs)
            # Re-fetch to get IDs for citation links
            created_references = list(
                Reference.objects.filter(document=document).order_by("id")
            )
            # Create a map of the references by index (in the document)
            references_by_index = {}
            for ref, reference_obj in zip(extraction_result.references, created_references):
                if ref.index is not None:
                    references_by_index[int(ref.index)] = reference_obj
        else:
            references_by_index = {}

        # Bulk-create section-citation links, skipping rows that already exist
        citation_links = []
        for sec in extraction_result.sections:
            section_obj = section_map.get(sec.heading)
            if not section_obj or not sec.citations:
                continue
            # Deduplicate citations within the same section
            seen_refs = set()
            for citation_index in sec.citations:
                ref_obj = references_by_index.get(int(citation_index))
                if not ref_obj or ref_obj.id in seen_refs:
                    continue
                seen_refs.add(ref_obj.id)
                citation_links.append(
                    SectionCitation(section=section_obj, reference=ref_obj)
                )
        if citation_links:
            # Bulk-create the citation links
            SectionCitation.objects.bulk_create(citation_links, ignore_conflicts=True)

        # Triples are grouped by normalized key so each triple only needs to be persisted once
        triples_persisted = 0
        grouped = {}
        for triple in triples:
            sub_norm = normalize_term(triple.sub)
            pred_norm = normalize_term(triple.pred)
            obj_norm = normalize_term(triple.obj)
            if not sub_norm or not pred_norm or not obj_norm:
                continue
            key = triple_key(sub_norm, pred_norm, obj_norm)
            grouped.setdefault(key, []).append(
                (triple, sub_norm, pred_norm, obj_norm)
            )

        evidence_rows = []
        now = timezone.now()
        for key, occurrences in grouped.items():
            # Pick the highest-confidence occurrence
            triple, sub_norm, pred_norm, obj_norm = max(
                occurrences, key=lambda item: float(item[0].conf)
            )
            section_obj = section_map.get(triple.section or "")
            confidence = self.compute_triple_confidence(
                document=document, section_obj=section_obj, triple=triple,
            )

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
                    "last_seen": now,
                },
            )
            if not created:
                # Update the confidence of the triple based on the existing confidence and the new confidence (biased towards existing confidence)
                triple_obj.confidence = min(
                    1.0, (triple_obj.confidence * 0.7 + confidence * 0.3) + 0.01
                )
                triple_obj.support_count += 1
                triple_obj.last_seen = now
                triple_obj.save(update_fields=["confidence", "support_count", "last_seen"])

            # For all occurrences of the triple, create a TripleEvidence object
            # This is because the confidence of the triple may be contributed by multiple documents or sections
            # This is also used to filter triples by document IDs in the GraphView
            for occ_triple, occ_sub, occ_pred, occ_obj in occurrences:
                occ_section_obj = section_map.get(occ_triple.section or "")
                occ_confidence = self.compute_triple_confidence(
                    document=document,
                    section_obj=occ_section_obj,
                    triple=occ_triple,
                )
                evidence_rows.append(
                    TripleEvidence(
                        triple=triple_obj,
                        document=document,
                        section=occ_section_obj,
                        confidence=occ_confidence,
                        source_method=(occ_triple.source or "")[:64],
                    )
                )
            triples_persisted += 1

        if evidence_rows:
            # Bulk-create the TripleEvidence objects
            TripleEvidence.objects.bulk_create(evidence_rows, batch_size=500)

        # Update the document status to completed
        document.status = Document.STATUS_COMPLETED
        document.save(update_fields=["status", "updated_at"])
        return {
            # Return the number of sections, references, and triples processed
            "sections": len(extraction_result.sections),
            "references": len(extraction_result.references),
            "triples": triples_persisted,
        }

    @staticmethod
    def compute_triple_confidence(*, document, section_obj, triple) -> float:
        """
        Compute the confidence of a triple based on the document and section.

        Args:
            document: The document that the triple belongs to
            section_obj: The section that the triple belongs to
            triple: The triple to compute the confidence of
        Returns:
            The confidence of the triple (0.0 to 1.0)
        """
        # Fetch the number of citations and citations reference count for the section
        if section_obj is not None:
            section_number_of_citations = section_obj.number_of_citations
            section_citations_reference_count = section_obj.citations_reference_count
        else:
            section_number_of_citations = 0
            section_citations_reference_count = 0

        # Compute the average number of citations per section
        document_citations_count = document.citations_count
        if section_number_of_citations == 0:
            section_citation_average = 0
        else:
            section_citation_average = section_citations_reference_count / section_number_of_citations

        # Compute the boost score based on number of citations in the associated section and the document
        section_boost = max(0.1, section_citation_average / 20000)
        document_boost = max(0.2, document_citations_count / 10000)
        total_boost = section_boost + document_boost

        # Return the confidence of the triple based on the boost score and the confidence of the triple
        return max(0.0, min(1.0, float(triple.conf) + total_boost))
