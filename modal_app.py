"""
Modal app for the UKG generator's GPU-heavy stage.

Modal only handles the GPU-heavy stage (generate_triples);

The VPS keeps PDF extraction, post-processing, and DB persistence.
Inputs/outputs are serialized as JSON-friendly types.
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
        # the HuggingFace download on every container boot.
        f"python -m spacy download {SPACY_MODEL}",
        "python -c \""
        "from gliner import GLiNER; "
        f"GLiNER.from_pretrained('{GLINER_MODEL}')\"",
    )
    .env({"UKG_SPAN_BATCH_SIZE": "16"})
    .add_local_dir(str(REPO_ROOT / "src"), "/app/src")
)

app = modal.App("ukg-generator")


@app.cls(
    image=image,
    gpu=["A10", "L4", "T4"],
    scaledown_window=300,
    timeout=900,
    enable_memory_snapshot=True,
)
class Pipeline:
    @modal.enter(snap=True)
    def load_models_to_cpu(self) -> None:
        """
        Pre-snapshot warm-up. Imports heavy modules and loads spaCy +
        GLiNER weights into CPU memory concurrently. Modal snapshots
        the process after this returns; future cold starts restore the
        snapshot instead of re-reading weights from disk.
        """
        import os
        import sys
        from concurrent.futures import ThreadPoolExecutor

        sys.path.insert(0, "/app/src")
        os.environ["UKG_DISABLE_GPU"] = "1"

        from generate_triples import load_gliner, load_spacy

        # Load the spaCy and GLiNER models in parallel.
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
        GLiNER weights onto CUDA
        """
        import os

        os.environ.pop("UKG_DISABLE_GPU", None)

        import generate_triples

        generate_triples.gpu_enabled = None
        generate_triples.ensure_gpu()

        try:
            import torch

            if torch.cuda.is_available():
                for name, model in list(generate_triples.gliner_cache.items()):
                    generate_triples.gliner_cache[name] = model.to("cuda")
        except Exception:
            pass

    @modal.method()
    def generate(
        self,
        sections: list[dict],
        entity_labels: dict[str, str] | list[str] | None = None,
        relation_labels: list[str] | None = None,
        span_model: str = GLINER_MODEL,
        model_name: str = SPACY_MODEL,
    ) -> list[dict]:
        """
        Run spaCy + GLiNER extraction on pre-parsed sections.

        Args:
            sections: list of Section dicts (heading, text, level, ...).
            entity_labels, relation_labels: forwarded to GLiNER. None lets
                                            the extractor's defaults apply.
            span_model: HuggingFace GLiNER model identifier.
            model_name: spaCy model identifier.

        Returns:
            list[dict] — each dict is a Triple._asdict() with keys
            sub, pred, obj, conf, source, section.
        """
        import sys

        sys.path.insert(0, "/app/src")

        from generate_triples import extract_triples
        from pipeline_types import Section

        section_objs = [Section(**s) for s in sections]
        triples = extract_triples(
            sections=section_objs,
            model_name=model_name,
            use_span_extraction=True,
            span_model=span_model,
            entity_labels=entity_labels,
            relation_labels=relation_labels,
        )
        return [t._asdict() for t in triples]
