"""
Data migration:
Seed the settings models (Blacklist/BlacklistTerm, LabelList/EntityLabel/RelationLabel, Ontology) from the 
read-only files under resources/ directory. This only runs once on initial deploy.
"""

import csv
import json
from pathlib import Path
from django.db import migrations

# CSV rule column: substring match vs exact entity match (stored as exact_match in the BlacklistTerm model)
RULE_TO_EXACT_MATCH = {
    "excl": False,
    "excl_only": True,
}

# The default blacklist name
DEFAULT_BLACKLIST_NAME = "default"

# The biomedical blacklist name
BIOMEDICAL_BLACKLIST_NAME = "biomedical"

# The default active label list (a label list is a set of entity and relation labels)
DEFAULT_ACTIVE_LABEL_LIST = "biomedical"


def resources_dir() -> Path:
    """
    Return the absolute path to the resources/ directory.
    The path is relative to the migrations folder.
    """
    # migrations -> kg -> backend -> repo root.
    return Path(__file__).resolve().parents[3] / "resources"


def seed_blacklists(apps):
    """
    Seed the default and biomedical blacklists.
    """
    Blacklist = apps.get_model("kg", "Blacklist")
    BlacklistTerm = apps.get_model("kg", "BlacklistTerm")

    blacklist_dir = resources_dir() / "blacklists"
    if not blacklist_dir.exists():
        return

    def load_csv(path: Path) -> list[tuple[str, str, str, str, str]]:
        """
        Load a blacklist from a CSV file
        The CSV file has the format: term,category,rule,subject,object

        Returns:
            A list of tuples, each containing the term, category, rule, subject, and object
        """
        # Read the CSV file and return the rows
        rows: list[tuple[str, str, str, str, str]] = []
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as fh:
            reader = csv.reader(fh)
            try:
                next(reader)
            except StopIteration:
                return rows
            for row in reader:
                # Ignore rows with less than 5 columns
                if len(row) < 5:
                    continue
                rows.append(
                    (
                        row[0].strip(),
                        row[1].strip(),
                        row[2].strip(),
                        row[3].strip(),
                        row[4].strip(),
                    )
                )
        return rows

    def upsert_blacklist(name: str, csv_path: Path, is_default: bool):
        """
        Update or insert a blacklist into the database.

        Input:
            name: The name of the blacklist
            csv_path: The path to the CSV file
            is_default: Whether the blacklist is the default blacklist
        """
        if not csv_path.exists():
            return
        blacklist, _ = Blacklist.objects.get_or_create(
            name=name,
            defaults={
                "source": "default",        # The source of the blacklist
                "is_default": is_default,   # Whether the blacklist is the default blacklist
                "is_enabled": True,         # Whether the blacklist is enabled
            },
        )

        # Preserve any existing rows on re-run; only seed if the blacklist is empty
        if blacklist.terms.exists():
            return
        
        rows = load_csv(csv_path)
        to_create = []
        seen: set[tuple[str, str]] = set()
        for term, category, rule, subject, object in rows:
            if not term:
                continue
            key = (term, category)

            # Ignore duplicate rows
            if key in seen:
                continue
            seen.add(key)
            exact_match = RULE_TO_EXACT_MATCH.get(rule, False)
            subject_on = subject == "1"
            object_on = object == "1"
            to_create.append(
                BlacklistTerm(
                    blacklist=blacklist,
                    term=term,
                    category=category,
                    exact_match=exact_match,
                    subject=subject_on,
                    object=object_on,
                    default_exact_match=exact_match,
                    default_subject=subject_on,
                    default_object=object_on,
                )
            )
        if to_create:
            BlacklistTerm.objects.bulk_create(to_create, batch_size=500)


    upsert_blacklist(
        DEFAULT_BLACKLIST_NAME,
        blacklist_dir / "default_blacklist.csv",
        is_default=True,
    )
    upsert_blacklist(
        BIOMEDICAL_BLACKLIST_NAME,
        blacklist_dir / "biomedical_blacklist.csv",
        is_default=False,
    )


def seed_label_lists(apps):
    """
    Seed the label lists from all the read-only (.json) files under resources/labels/ directory.
    """
    LabelList = apps.get_model("kg", "LabelList")
    EntityLabel = apps.get_model("kg", "EntityLabel")
    RelationLabel = apps.get_model("kg", "RelationLabel")

    labels_dir = resources_dir() / "labels"
    if not labels_dir.exists():
        return

    for json_path in sorted(labels_dir.glob("*.json")):
        # Strip the trailing "_labels" suffix from the filename stem like "biomedical_labels.json" -> "biomedical"
        name = json_path.stem
        if name.endswith("_labels"):
            name = name[: -len("_labels")]

        with json_path.open("r", encoding="utf-8") as fh:
            try:
                payload = json.load(fh)
            except json.JSONDecodeError:
                continue

        # Get the entity and relation labels from the payload
        entity_labels = payload.get("entity_labels", {}) or {}
        relation_labels = payload.get("relation_labels", []) or []

        label_list, created = LabelList.objects.get_or_create(
            name=name,
            defaults={
                "source": "default",
                "is_active": False,
                "default_payload": {
                    "entity_labels": entity_labels,
                    "relation_labels": relation_labels,
                },
            },
        )

        # If the label list already exists, skip it
        if not created:
            continue

        # Convert the entity labels to a list of tuples (label, description)
        if isinstance(entity_labels, dict):
            entity_iter = list(entity_labels.items())
        else:
            # If the entity labels are not a dictionary, use empty descriptions for each label
            entity_iter = [(value, "") for value in entity_labels]

        EntityLabel.objects.bulk_create(
            [
                EntityLabel(
                    label_list=label_list,
                    label=str(label),
                    description=str(desc or ""),
                    order=idx,
                )
                for idx, (label, desc) in enumerate(entity_iter)
            ]
        )

        RelationLabel.objects.bulk_create(
            [
                RelationLabel(label_list=label_list, label=str(label), order=idx)
                for idx, label in enumerate(relation_labels)
            ]
        )

    # Default active list: biomedical if present, otherwise the first default list
    if not LabelList.objects.filter(is_active=True).exists():
        active = (
            LabelList.objects.filter(name=DEFAULT_ACTIVE_LABEL_LIST).first()
            or LabelList.objects.filter(source="default").order_by("name").first()
        )
        if active is not None:
            active.is_active = True
            active.save(update_fields=["is_active", "updated_at"])


def seed_ontologies(apps):
    """
    Seed the ontologies from all the read-only (.txt) files under resources/ontologies/ directory.
    """
    Ontology = apps.get_model("kg", "Ontology")

    ontology_dir = resources_dir() / "ontologies"
    if not ontology_dir.exists():
        return

    # This only stores the path to the ontology file in the database
    # The file itself is not stored in the database
    for txt_path in sorted(ontology_dir.glob("*.txt")):
        Ontology.objects.get_or_create(
            name=txt_path.stem,
            defaults={
                "source": "default",
                "is_enabled": True,
                "source_path": str(txt_path.resolve()),
            },
        )


def seed_forward(apps, schema_editor):
    # Seed all the settings models
    seed_blacklists(apps)
    seed_label_lists(apps)
    seed_ontologies(apps)


def seed_reverse(apps, schema_editor):
    """
    Logic for reversing the migration.
    """
    # Only clear default-sourced rows so custom user data survives reversal
    Blacklist = apps.get_model("kg", "Blacklist")
    LabelList = apps.get_model("kg", "LabelList")
    Ontology = apps.get_model("kg", "Ontology")
    Blacklist.objects.filter(source="default").delete()
    LabelList.objects.filter(source="default").delete()
    Ontology.objects.filter(source="default").delete()


class Migration(migrations.Migration):
    # Apply the migration forward

    dependencies = [
        ("kg", "0004_settings"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
