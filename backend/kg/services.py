"""
The file contains the services (containing all the pipeline modules) for creating the knowledge graph from 
the processed documents (PDFs).
"""

import sys
from dataclasses import asdict
from pathlib import Path

import modal
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


# Identifiers for the Modal deployment that owns the GPU pipeline. Must match
# `app = modal.App("ukg-generator")` and the `Pipeline` class in modal_app.py.
MODAL_APP_NAME = "ukg-generator"
MODAL_PIPELINE_CLS_NAME = "Pipeline"


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
        Lazy-import the pipeline modules the VPS still runs locally:
        PDF extraction (extraction_module), the lightweight resource
        loaders (pipeline_io), and the post-processing helpers
        (pipeline_filters: blacklist filtering + ontology boosting).
        The GPU stage (spaCy + GLiNER) runs on Modal, so generate_triples
        is intentionally not imported here.
        """
        src_text = str(self.src_dir)
        if src_text not in sys.path:
            sys.path.insert(0, src_text)

        try:
            from extraction_module import extract_json_data, post_process_json_data
            from pipeline_io import build_blacklist_sets, load_ontology_terms
            from pipeline_filters import OntologyFilter, filter_triples
            from pipeline_types import Triple
        except ModuleNotFoundError as exc:
            raise PipelineImportError("Could not import pipeline modules from src/") from exc
        return {
            "extract_json_data": extract_json_data,
            "post_process_json_data": post_process_json_data,
            "build_blacklist_sets": build_blacklist_sets,
            "load_ontology_terms": load_ontology_terms,
            "filter_triples": filter_triples,
            "OntologyFilter": OntologyFilter,
            "Triple": Triple,
        }

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
    def db_ontology_terms(load_ontology_terms) -> frozenset[str]:
        """
        Read every enabled ontology (default `resources/` files and uploaded
        `media/ontologies/` files) into a single in-memory term set.

        The merged set, rather than file paths, is the value passed downstream
        to `generate_triples` — callers that run the pipeline out-of-process
        (e.g. on Modal) therefore don't need access to the VPS filesystem.
        """
        paths: list[str] = []
        for ontology in Ontology.objects.filter(is_enabled=True):
            resolved = ontology.resolved_path()
            if resolved:
                paths.append(resolved)
        return load_ontology_terms(tuple(paths))

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
        # Import the pipeline modules (extraction + lightweight loaders +
        # filter helpers; the GPU stage lives on Modal).
        modules = self.import_pipeline_modules()
        extract_json_data = modules["extract_json_data"]
        post_process_json_data = modules["post_process_json_data"]
        build_blacklist_sets = modules["build_blacklist_sets"]
        load_ontology_terms = modules["load_ontology_terms"]
        filter_triples = modules["filter_triples"]
        OntologyFilter = modules["OntologyFilter"]
        Triple = modules["Triple"]

        # Load the blacklist/ontology/label configuration from the settings DB
        blacklist_sets = self.build_db_blacklist_sets(build_blacklist_sets)
        ontology_terms = self.db_ontology_terms(load_ontology_terms)
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

        # Run the GPU stage on Modal to generate triples.
        raw_triples = self.generate_triples_on_modal(
            sections=extraction_result.sections,
            entity_labels=entity_labels,
            relation_labels=relation_labels,
            triple_cls=Triple,
        )

        # Apply post-processing: triple filtering and ontology boosting.
        filtered_triples = filter_triples(raw_triples, blacklist_sets)
        if ontology_terms:
            filtered_triples = OntologyFilter(ontology_terms).boost(
                filtered_triples, require_match=False,
            )

        # Persist the extraction result and emitted triples atomically
        with transaction.atomic():
            return self.persist_extraction(
                document=document,
                extraction_result=extraction_result,
                triples=filtered_triples,
            )

    @staticmethod
    def generate_triples_on_modal(
        *,
        sections,
        entity_labels,
        relation_labels,
        triple_cls,
    ) -> list:
        """
        Invoke the deployed Modal Pipeline.generate method and rebuild
        `pipeline_types.Triple` namedtuples from its dict payload so the
        downstream filtering helpers work unchanged.
        """
        pipeline = modal.Cls.from_name(MODAL_APP_NAME, MODAL_PIPELINE_CLS_NAME)()
        triple_dicts = pipeline.generate.remote(
            sections=[asdict(sec) for sec in sections],
            entity_labels=entity_labels,
            relation_labels=relation_labels,
        )
        return [triple_cls(**t) for t in triple_dicts]

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
