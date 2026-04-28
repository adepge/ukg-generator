"""
Modal app for the UKG generator's GPU-heavy stage.

Only `generate_triples` (spaCy + GLiNER) runs here; the VPS keeps PDF
extraction, post-processing, and DB persistence. Inputs and outputs use
plain JSON-friendly types so the VPS never has to import the heavy
pipeline modules — and therefore doesn't need spaCy / GLiNER / torch
installed.
"""

from __future__ import annotations

from pathlib import Path

import modal

REPO_ROOT = Path(__file__).resolve().parent

GLINER_MODEL = "knowledgator/gliner-relex-large-v0.5"
SPACY_MODEL = "en_core_web_lg"

image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install_from_requirements(str(REPO_ROOT / "requirements-modal.txt"))
    .run_commands(
        # Bake spaCy + GLiNER weights into the image so cold starts skip
        # the (slow) HuggingFace download on every container boot.
        f"python -m spacy download {SPACY_MODEL}",
        "python -c \""
        "from gliner import GLiNER; "
        f"GLiNER.from_pretrained('{GLINER_MODEL}')\"",
    )
    .add_local_dir(str(REPO_ROOT / "src"), "/app/src")
)

app = modal.App("ukg-generator")


@app.cls(
    image=image,
    gpu="T4",
    scaledown_window=300,
    timeout=900,
    enable_memory_snapshot=True,
    # Set `min_containers=1` here if you want to eliminate cold starts
    # entirely at the cost of a permanently-reserved T4. For a low-traffic
    # research deployment the snapshot path below is usually fast enough
    # (~3-5 s) without paying for an always-on GPU.
)
class Pipeline:
    @modal.enter(snap=True)
    def load_models_to_cpu(self) -> None:
        """
        Pre-snapshot warm-up. Imports heavy modules and loads spaCy +
        GLiNER weights into CPU memory concurrently. Modal snapshots
        the process after this returns; future cold starts restore the
        snapshot instead of re-reading weights from disk.

        GPU initialisation is deferred to `move_models_to_gpu` — CUDA
        contexts cannot be captured by memory snapshotting.
        """
        import os
        import sys
        from concurrent.futures import ThreadPoolExecutor

        sys.path.insert(0, "/app/src")

        # Force CPU-only loading during the snapshot phase. The GPU is
        # not attached at this point, and CUDA state can't be snapshotted.
        os.environ["UKG_DISABLE_GPU"] = "1"

        from generate_triples import load_gliner, load_spacy

        # spaCy and GLiNER have no inter-dependency; load them in
        # parallel to take advantage of Modal's high disk bandwidth.
        with ThreadPoolExecutor(max_workers=2) as pool:
            spacy_future = pool.submit(load_spacy, SPACY_MODEL)
            gliner_future = pool.submit(load_gliner, GLINER_MODEL)
            spacy_future.result()
            gliner_future.result()

    @modal.enter()
    def move_models_to_gpu(self) -> None:
        """
        Post-snapshot hook (runs on every container start, cold or
        restored). Re-enables GPU usage and moves the already-loaded
        GLiNER weights onto CUDA — they were placed on CPU in
        `load_models_to_cpu` so the snapshot would be valid.
        """
        import os

        os.environ.pop("UKG_DISABLE_GPU", None)

        import generate_triples

        # Reset the cached GPU-availability flag set to False during
        # the snap=True hook, then re-detect with a real GPU attached.
        generate_triples.gpu_enabled = None
        generate_triples.ensure_gpu()

        try:
            import torch

            if torch.cuda.is_available():
                for name, model in list(generate_triples.gliner_cache.items()):
                    generate_triples.gliner_cache[name] = model.to("cuda")
        except Exception:
            # If CUDA init fails, fall back to CPU rather than crashing
            # the worker — the pipeline is still correct, just slower.
            pass

    @modal.method()
    def generate(
        self,
        sections: list[dict],
        blacklist_sets: tuple[list[str], list[str], list[str], list[str]],
        ontology_terms: list[str],
        entity_labels: dict[str, str] | list[str] | None,
        relation_labels: list[str] | None,
        require_ontology_match: bool = False,
        span_model: str = GLINER_MODEL,
        model_name: str = SPACY_MODEL,
    ) -> list[dict]:
        """
        Run triple generation on pre-extracted sections.

        Args:
            sections: list of Section dicts (heading, text, level, ...).
            blacklist_sets: (subject_excl_str, object_excl_str,
                             subject_excl_word, object_excl_word).
            ontology_terms: lowercased ontology term list (frozenset on the
                            VPS, sent as list for JSON-friendly transport).
            entity_labels, relation_labels: forwarded to GLiNER.
            require_ontology_match: drop triples whose subject/object isn't
                                    in the ontology term set.

        Returns:
            list[dict] — each dict is a Triple._asdict(): keys sub, pred,
            obj, conf, source, section.
        """
        import sys

        sys.path.insert(0, "/app/src")

        from generate_triples import generate_triples
        from pipeline_types import Section

        section_objs = [Section(**s) for s in sections]
        triples = generate_triples(
            sections=section_objs,
            model_name=model_name,
            blacklist_sets=blacklist_sets,
            ontology_terms=frozenset(ontology_terms),
            entity_labels=entity_labels,
            relation_labels=relation_labels,
            require_ontology_match=require_ontology_match,
            use_span_extraction=True,
            span_model=span_model,
            output_path=None,
        )
        return [t._asdict() for t in triples]
