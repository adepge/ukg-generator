"""
This file contains the API views for the settings panel (blacklists, label lists, ontologies) in the UKG web application (backend).
All routes are mounted under `/api/settings/`.
"""

import csv
import io
from pathlib import Path

from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from rest_framework import parsers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Blacklist,
    BlacklistTerm,
    EntityLabel,
    LabelList,
    Ontology,
    RelationLabel,
    SETTINGS_SOURCE_CUSTOM,
    SETTINGS_SOURCE_DEFAULT,
)
from .serializers import (
    BlacklistSerializer,
    BlacklistTermSerializer,
    EntityLabelSerializer,
    LabelListDetailSerializer,
    LabelListSerializer,
    OntologySerializer,
    RelationLabelSerializer,
)


# ================================================
# Helpers
# ================================================

BLACKLIST_CSV_HEADER = ["term", "category", "rule", "subject", "object"]
RULE_TO_EXACT_MATCH = {"excl": False, "excl_only": True}
VALID_RULES = frozenset(RULE_TO_EXACT_MATCH.keys())


def clean_filename_stem(name: str) -> str:
    """
    Normalize a user-provided filename into a safe, unique model name.
    Example: "specific_subject.txt" -> "specific_subject"
    """
    stem = Path(name).stem.strip()
    if not stem:
        return "uploaded"
    # Collapse whitespace and disallow forward slashes
    return stem.replace("/", "_")


def parse_blacklist_csv(file_obj) -> tuple[list[dict], list[str]]:
    """
    Parse an uploaded blacklist CSV stream.
    This is used to validate the uploaded CSV file and convert it into a list of dictionaries.
    The headers of the CSV file are expected to be: term,category,rule,subject,object
        - term: The term to blacklist
        - category: The category of the term
        - rule: The rule to apply to the term (excl_only or excl)
        - subject: Whether the term is a subject (1) or object (0)
        - object: Whether the term is an object (1) or subject (0)

    Input:
        file_obj: The uploaded CSV file object
    Returns:
        A tuple of (rows, errors) where each row is a dict with keys term/category/exact_match/subject/object
        and errors is a list of human-readable validation errors
    """
    try:
        raw = file_obj.read()
    except Exception as exc:
        return [], [f"Could not read upload: {exc}"]

    # Decode the uploaded file into a string
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="ignore")
    else:
        text = raw

    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return [], ["CSV is empty."]

    # Validate the header of the CSV file
    header_norm = [col.strip().lower() for col in header]
    if header_norm != BLACKLIST_CSV_HEADER:
        return [], [
            "CSV header mismatch. Expected: "
            + ",".join(BLACKLIST_CSV_HEADER)
            + f". Got: {','.join(header_norm)}."
        ]

    # Parse the rows of the CSV file
    rows: list[dict] = []
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for i, row in enumerate(reader, start=2):
        # Skip empty rows
        if not row or all(not (cell or "").strip() for cell in row):
            continue
        if len(row) < 5:
            errors.append(f"Row {i}: expected 5 columns, got {len(row)}.")
            continue
        term = (row[0] or "").strip()
        category = (row[1] or "").strip()
        rule = (row[2] or "").strip()
        subject = (row[3] or "").strip()
        object_ = (row[4] or "").strip()

        # Validate the columns of each row of the CSV file
        if not term:
            errors.append(f"Row {i}: `term` cannot be empty.")
            continue
        if rule not in VALID_RULES:
            errors.append(
                f"Row {i}: `rule` must be one of {sorted(VALID_RULES)} (got {rule!r})."
            )
            continue
        if subject not in {"0", "1"}:
            errors.append(f"Row {i}: `subject` must be 0 or 1 (got {subject!r}).")
            continue
        if object_ not in {"0", "1"}:
            errors.append(f"Row {i}: `object` must be 0 or 1 (got {object_!r}).")
            continue

        key = (term, category)
        if key in seen:
            # Silently skip exact duplicates to stay tolerant
            continue
        seen.add(key)

        rows.append(
            {
                "term": term,
                "category": category,
                "exact_match": RULE_TO_EXACT_MATCH[rule],
                "subject": subject == "1",
                "object": object_ == "1",
            }
        )

    return rows, errors


# ================================================
# Blacklist views
# ================================================

class BlacklistListView(APIView):
    """
    List all blacklists available in the database.

    Input:
        request: The HTTP request object
    Returns:
        A Response object with all blacklists
    """

    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get(self, request):
        blacklists = Blacklist.objects.all().order_by("-is_default", "name")
        return Response(BlacklistSerializer(blacklists, many=True).data)


class BlacklistUploadView(APIView):
    """
    Upload a CSV file to create a new custom blacklist.
    Input:
        request: The HTTP request object
    Returns:
        A Response object with the new Blacklist object
    """

    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "Expected multipart field `file`."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not upload.name.lower().endswith(".csv"):
            return Response(
                {"detail": "Only `.csv` files are supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse the uploaded CSV file
        rows, errors = parse_blacklist_csv(upload)
        if errors:
            return Response(
                {"detail": "Invalid blacklist CSV.", "errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not rows:
            return Response(
                {"detail": "The CSV contained no valid rows."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Derive a unique blacklist name from the uploaded filename
        requested_name = request.data.get("name") or clean_filename_stem(upload.name)
        name = requested_name
        suffix = 2
        while Blacklist.objects.filter(name=name).exists():
            name = f"{requested_name}_{suffix}"
            suffix += 1

        # Rewind and store the uploaded file via the FileField
        try:
            upload.seek(0)
        except Exception:
            pass

        # Create the blacklist and bulk-create the terms from the uploaded CSV file
        with transaction.atomic():
            blacklist = Blacklist.objects.create(
                name=name,
                source=SETTINGS_SOURCE_CUSTOM,
                is_default=False,
                is_enabled=True,
                file=upload,
            )
            BlacklistTerm.objects.bulk_create(
                [
                    BlacklistTerm(
                        blacklist=blacklist,
                        term=row["term"],
                        category=row["category"],
                        exact_match=row["exact_match"],
                        subject=row["subject"],
                        object=row["object"],
                        default_exact_match=row["exact_match"],
                        default_subject=row["subject"],
                        default_object=row["object"],
                    )
                    for row in rows
                ],
                batch_size=500,
            )

        return Response(
            BlacklistSerializer(blacklist).data,
            status=status.HTTP_201_CREATED,
        )


class BlacklistDetailView(APIView):
    """
    Retrieve or delete a single blacklist.

    Input:
        request: The HTTP request object
        blacklist_id: The ID of the blacklist to retrieve or delete
    Returns:
        A Response object with the blacklist terms
    """

    def get(self, request, blacklist_id: int):
        try:
            blacklist = Blacklist.objects.get(id=blacklist_id)
        except Blacklist.DoesNotExist:
            return Response({"detail": "Blacklist not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get the unique categories of the blacklist terms
        categories = sorted(
            {
                (category or "")
                for category in blacklist.terms.values_list("category", flat=True)
                .distinct()
            }
        )
        return Response(
            {
                **BlacklistSerializer(blacklist).data,
                "categories": categories,
            }
        )

    def delete(self, request, blacklist_id: int):
        try:
            blacklist = Blacklist.objects.get(id=blacklist_id)
        except Blacklist.DoesNotExist:
            return Response({"detail": "Blacklist not found."}, status=status.HTTP_404_NOT_FOUND)

        if blacklist.is_default:
            return Response(
                {"detail": "The default blacklist cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Clean up the uploaded file from disk if present
        if blacklist.file:
            try:
                blacklist.file.delete(save=False)
            except Exception:
                pass

        blacklist.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BlacklistTermsView(APIView):
    """
    List blacklist terms with pagination and optional filters.

    Input:
        request: The HTTP request object
        blacklist_id: The ID of the blacklist to list the terms for
    Returns:
        A Response object with the blacklist terms
    """

    def get(self, request, blacklist_id: int):
        try:
            blacklist = Blacklist.objects.get(id=blacklist_id)
        except Blacklist.DoesNotExist:
            return Response({"detail": "Blacklist not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get the query and category filters from the request
        query = (request.GET.get("q") or "").strip().lower()
        category = request.GET.get("category")

        terms_qs = blacklist.terms.all()
        if category is not None and category != "":
            terms_qs = terms_qs.filter(category=category)
        if query:
            terms_qs = terms_qs.filter(term__icontains=query)

        # Get the limit and offset from the request
        # The offset is used to paginate the results
        try:
            limit = int(request.GET.get("limit", 1000))
        except (TypeError, ValueError):
            limit = 1000
        try:
            offset = int(request.GET.get("offset", 0))
        except (TypeError, ValueError):
            offset = 0

        # Ensure the limit and offset are within valid ranges
        limit = max(1, min(limit, 20000))
        offset = max(0, min(offset, 19999))

        # Get the total number of terms and the paginated results
        total = terms_qs.count()
        page = terms_qs[offset : offset + limit]
        return Response(
            {
                "count": total,
                "limit": limit,
                "offset": offset,
                "results": BlacklistTermSerializer(page, many=True).data,
            }
        )


class BlacklistTermDetailView(APIView):
    """
    Patch a single blacklist term with its configuration options (exact_match / subject / object).

    Input:
        request: The HTTP request object
        blacklist_id: The ID of the blacklist to patch the term for
        term_id: The ID of the term to patch
    Returns:
        A Response object with the patched term
    """

    def patch(self, request, blacklist_id: int, term_id: int):
        # Get the term from database to patch.
        try:
            term = BlacklistTerm.objects.select_related("blacklist").get(
                id=term_id, blacklist_id=blacklist_id
            )
        except BlacklistTerm.DoesNotExist:
            return Response({"detail": "Term not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = request.data or {}
        updated_fields: list[str] = []
        for field in ("exact_match", "subject", "object"):
            if field in payload:
                value = payload[field]
                if not isinstance(value, bool):
                    return Response(
                        {"detail": f"`{field}` must be a boolean."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                setattr(term, field, value)
                updated_fields.append(field)

        if updated_fields:
            term.save(update_fields=updated_fields)

        return Response(BlacklistTermSerializer(term).data)


class BlacklistResetView(APIView):
    """
    Reset every term's current state to its default values. The default values are the values that were used to seed the blacklist.
    This allows the user to reset a given blacklist to its original state.
    
    Input:
        request: The HTTP request object
        blacklist_id: The ID of the blacklist to reset the terms for
    Returns:
        A Response object with the reset terms
    """

    def post(self, request, blacklist_id: int):
        try:
            blacklist = Blacklist.objects.get(id=blacklist_id)
        except Blacklist.DoesNotExist:
            return Response({"detail": "Blacklist not found."}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            # Update the terms to their default values
            blacklist.terms.update(
                exact_match=F("default_exact_match"),
                subject=F("default_subject"),
                object=F("default_object"),
            )

        return Response({"detail": "Blacklist reset to defaults."})


class BlacklistToggleView(APIView):
    """
    Enable or disable a blacklist.

    Input:
        request: The HTTP request object
        blacklist_id: The ID of the blacklist to enable or disable
    Returns:
        A Response object with the enabled or disabled blacklist
    """

    def post(self, request, blacklist_id: int):
        try:
            blacklist = Blacklist.objects.get(id=blacklist_id)
        except Blacklist.DoesNotExist:
            return Response({"detail": "Blacklist not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = request.data or {}
        is_enabled = payload.get("is_enabled")
        if not isinstance(is_enabled, bool):
            return Response(
                {"detail": "`is_enabled` must be a boolean."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # The default blacklist cannot be disabled (it is always applied during pipeline runs)
        if blacklist.is_default and not is_enabled:
            return Response(
                {"detail": "The default blacklist cannot be disabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        blacklist.is_enabled = is_enabled
        blacklist.save(update_fields=["is_enabled", "updated_at"])
        return Response(BlacklistSerializer(blacklist).data)


class BlacklistDownloadView(APIView):
    """
    Download the current state of a blacklist as a CSV file.

    Input:
        request: The HTTP request object
        blacklist_id: The ID of the blacklist to download
    Returns:
        A Response object with the downloaded CSV file
    """

    def get(self, request, blacklist_id: int):
        try:
            blacklist = Blacklist.objects.get(id=blacklist_id)
        except Blacklist.DoesNotExist:
            return Response({"detail": "Blacklist not found."}, status=status.HTTP_404_NOT_FOUND)

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(BLACKLIST_CSV_HEADER)
        for term in blacklist.terms.all().order_by("term", "id"):
            writer.writerow(
                [
                    term.term,
                    term.category,
                    "excl_only" if term.exact_match else "excl",
                    "1" if term.subject else "0",
                    "1" if term.object else "0",
                ]
            )

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{blacklist.name}_blacklist.csv"'
        )
        return response


# ================================================
# Label list views
# ================================================


class LabelListListView(APIView):
    """
    List label lists and create custom ones.
    Label lists are used to scope the entities and relations that are extracted from the text using
    the span relation extractor.

    Input:
        request: The HTTP request object
    Returns:
        A Response object with the label lists
    """

    def get(self, request):
        # Get all label lists ordered by activity (active first) and name
        label_lists = LabelList.objects.all().order_by("-is_active", "name")
        return Response(LabelListSerializer(label_lists, many=True).data)

    def post(self, request):
        payload = request.data or {}
        name = (payload.get("name") or "").strip()
        if not name:
            return Response(
                {"detail": "`name` is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure that the label list name is unique
        if LabelList.objects.filter(name=name).exists():
            return Response(
                {"detail": f"A label list named {name!r} already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entity_payload = payload.get("entity_labels") or []
        relation_payload = payload.get("relation_labels") or []

        if not isinstance(entity_payload, list) or not isinstance(relation_payload, list):
            return Response(
                {"detail": "`entity_labels` and `relation_labels` must be arrays."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse the entity labels
        # The entity labels are expected to be a list of tuples (label, description)
        parsed_entities: list[tuple[str, str]] = [] 
        seen_entities: set[str] = set()
        for idx, item in enumerate(entity_payload):
            if isinstance(item, str):
                label, description = item.strip(), ""
            elif isinstance(item, dict):
                label = (item.get("label") or "").strip()
                description = (item.get("description") or "").strip()
            else:
                return Response(
                    {"detail": f"entity_labels[{idx}] must be a string or an object."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not label:
                return Response(
                    {"detail": f"entity_labels[{idx}] has an empty label."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Don't allow duplicate entity labels
            if label in seen_entities:
                return Response(
                    {"detail": f"entity_labels[{idx}] duplicate label {label!r}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            seen_entities.add(label)
            parsed_entities.append((label, description))


        # Parse the relation labels
        # The relation labels are expected to be a list of strings
        parsed_relations: list[str] = []
        seen_relations: set[str] = set()
        for idx, item in enumerate(relation_payload):
            if not isinstance(item, str):
                return Response(
                    {"detail": f"relation_labels[{idx}] must be a string."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            label = item.strip()
            if not label:
                return Response(
                    {"detail": f"relation_labels[{idx}] is empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Don't allow duplicate relation labels
            if label in seen_relations:
                return Response(
                    {"detail": f"relation_labels[{idx}] duplicate label {label!r}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            seen_relations.add(label)
            parsed_relations.append(label)

        with transaction.atomic():
            label_list = LabelList.objects.create(
                name=name,
                source=SETTINGS_SOURCE_CUSTOM,
                is_active=False,
                default_payload={},
            )
            EntityLabel.objects.bulk_create(
                [
                    EntityLabel(
                        label_list=label_list,
                        label=label,
                        description=description,
                        order=idx,
                    )
                    for idx, (label, description) in enumerate(parsed_entities)
                ]
            )
            RelationLabel.objects.bulk_create(
                [
                    RelationLabel(label_list=label_list, label=label, order=idx)
                    for idx, label in enumerate(parsed_relations)
                ]
            )

        return Response(
            LabelListDetailSerializer(label_list).data,
            status=status.HTTP_201_CREATED,
        )


class LabelListDetailView(APIView):
    """
    Retrieve or delete a single label list.

    Input:
        request: The HTTP request object
        label_list_id: The ID of the label list to retrieve or delete
    Returns:
        A Response object with the label list
    """

    def get(self, request, label_list_id: int):
        try:
            label_list = LabelList.objects.get(id=label_list_id)
        except LabelList.DoesNotExist:
            return Response({"detail": "Label list not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(LabelListDetailSerializer(label_list).data)

    def delete(self, request, label_list_id: int):
        try:
            label_list = LabelList.objects.get(id=label_list_id)
        except LabelList.DoesNotExist:
            return Response({"detail": "Label list not found."}, status=status.HTTP_404_NOT_FOUND)

        # Default label lists cannot be deleted (default label lists are ones that are not user-created but provided by the application)
        if label_list.source == SETTINGS_SOURCE_DEFAULT:
            return Response(
                {"detail": "Default label lists cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        was_active = label_list.is_active
        label_list.delete()

        if was_active:
            # Ensure at least one label list remains active if any exist
            replacement = LabelList.objects.order_by(
                "-source", "name"
            ).first()  # prefer default over custom alphabetically
            if replacement is not None:
                replacement.is_active = True
                replacement.save(update_fields=["is_active", "updated_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class LabelListActivateView(APIView):
    """
    Mark the label list active and deactivate all others.
    
    Input:
        request: The HTTP request object
        label_list_id: The ID of the label list to activate
    Returns:
        A Response object with the activated label list
    """

    def post(self, request, label_list_id: int):
        try:
            label_list = LabelList.objects.get(id=label_list_id)
        except LabelList.DoesNotExist:
            return Response({"detail": "Label list not found."}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            LabelList.objects.exclude(id=label_list.id).update(is_active=False)
            if not label_list.is_active:
                label_list.is_active = True
                label_list.save(update_fields=["is_active", "updated_at"])

        return Response(LabelListSerializer(label_list).data)


class LabelListResetView(APIView):
    """
    Reset a default label list back to its default values.
    This allows the user to reset a given default label list to its original state.
    Custom label lists cannot be reset, only edited.
    
    Input:
        request: The HTTP request object
        label_list_id: The ID of the label list to reset
    Returns:
        A Response object with the reset label list
    """
 
    def post(self, request, label_list_id: int):
        try:
            label_list = LabelList.objects.get(id=label_list_id)
        except LabelList.DoesNotExist:
            return Response({"detail": "Label list not found."}, status=status.HTTP_404_NOT_FOUND)

        if label_list.source != SETTINGS_SOURCE_DEFAULT:
            return Response(
                {"detail": "Only default label lists can be reset."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the default payload for the label list
        payload = label_list.default_payload or {}
        entity_payload = payload.get("entity_labels", {}) or {}
        relation_payload = payload.get("relation_labels", []) or []

        # Check if the entity payload is a dictionary (descriptions are optional)
        if isinstance(entity_payload, dict):
            entity_iter = list(entity_payload.items())
        else:
            entity_iter = [(value, "") for value in entity_payload]

        # Delete all existing entity and relation labels and recreate them with the default values
        with transaction.atomic():
            label_list.entity_labels.all().delete()
            label_list.relation_labels.all().delete()
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
                    for idx, label in enumerate(relation_payload)
                ]
            )

        return Response(LabelListDetailSerializer(label_list).data)


class EntityLabelListView(APIView):
    """
    Create a new entity label inside a label list.

    Input:
        request: The HTTP request object
        label_list_id: The ID of the label list to create the entity label for
    Returns:
        A Response object with the created entity label
    """

    def post(self, request, label_list_id: int):
        # Get the label list to create the entity label for
        try:
            label_list = LabelList.objects.get(id=label_list_id)
        except LabelList.DoesNotExist:
            return Response({"detail": "Label list not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = request.data or {}
        label = (payload.get("label") or "").strip()
        description = (payload.get("description") or "").strip()
        if not label:
            return Response(
                {"detail": "`label` is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if label_list.entity_labels.filter(label=label).exists():
            return Response(
                {"detail": f"Entity label {label!r} already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the entity label
        next_order = label_list.entity_labels.count()
        entity = EntityLabel.objects.create(
            label_list=label_list,
            label=label,
            description=description,
            order=next_order,
        )
        return Response(
            EntityLabelSerializer(entity).data, status=status.HTTP_201_CREATED
        )


class EntityLabelDetailView(APIView):
    """
    Patch or delete a single entity label.

    Input:
        request: The HTTP request object
        label_list_id: The ID of the label list to patch the entity label for
        entity_id: The ID of the entity label to patch or delete
    Returns:
        A Response object with the patched or deleted entity label
    """

    def patch(self, request, label_list_id: int, entity_id: int):
        try:
            entity = EntityLabel.objects.get(id=entity_id, label_list_id=label_list_id)
        except EntityLabel.DoesNotExist:
            return Response(
                {"detail": "Entity label not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = request.data or {}
        updated_fields: list[str] = []

        if "label" in payload:
            new_label = (payload.get("label") or "").strip()
            if not new_label:
                return Response(
                    {"detail": "`label` cannot be empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Don't allow duplicate entity labels when patching an existing one
            if (
                new_label != entity.label
                and EntityLabel.objects.filter(label_list_id=label_list_id, label=new_label).exists()
            ):
                return Response(
                    {"detail": f"Entity label {new_label!r} already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            entity.label = new_label
            updated_fields.append("label")

        # Update the entity label description
        if "description" in payload:
            entity.description = (payload.get("description") or "").strip()
            updated_fields.append("description")

        if updated_fields:
            entity.save(update_fields=updated_fields)
        return Response(EntityLabelSerializer(entity).data)

    def delete(self, request, label_list_id: int, entity_id: int):
        try:
            entity = EntityLabel.objects.get(id=entity_id, label_list_id=label_list_id)
        except EntityLabel.DoesNotExist:
            return Response(
                {"detail": "Entity label not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        entity.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RelationLabelListView(APIView):
    """
    Create a new relation label inside a label list.

    Input:
        request: The HTTP request object
        label_list_id: The ID of the label list to create the relation label for
    Returns:
        A Response object with the created relation label
    """

    def post(self, request, label_list_id: int):
        # Get the label list to create the relation label for
        try:
            label_list = LabelList.objects.get(id=label_list_id)
        except LabelList.DoesNotExist:
            return Response({"detail": "Label list not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = request.data or {}
        label = (payload.get("label") or "").strip()
        if not label:
            return Response(
                {"detail": "`label` is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Don't allow duplicate relation labels
        if label_list.relation_labels.filter(label=label).exists():
            return Response(
                {"detail": f"Relation label {label!r} already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        next_order = label_list.relation_labels.count()
        relation = RelationLabel.objects.create(
            label_list=label_list,
            label=label,
            order=next_order,
        )
        return Response(
            RelationLabelSerializer(relation).data, status=status.HTTP_201_CREATED
        )


class RelationLabelDetailView(APIView):
    """
    Patch or delete a single relation label.
    
    Input:
        request: The HTTP request object
        label_list_id: The ID of the label list to patch the relation label for
        relation_id: The ID of the relation label to patch or delete
    Returns:
        A Response object with the patched or deleted relation label
    """

    def patch(self, request, label_list_id: int, relation_id: int):
        try:
            relation = RelationLabel.objects.get(id=relation_id, label_list_id=label_list_id)
        except RelationLabel.DoesNotExist:
            return Response(
                {"detail": "Relation label not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = request.data or {}
        if "label" in payload:
            new_label = (payload.get("label") or "").strip()
            if not new_label:
                return Response(
                    {"detail": "`label` cannot be empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Don't allow duplicate relation labels when patching an existing one
            if (
                new_label != relation.label
                and RelationLabel.objects.filter(label_list_id=label_list_id, label=new_label).exists()
            ):
                return Response(
                    {"detail": f"Relation label {new_label!r} already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            relation.label = new_label
            relation.save(update_fields=["label"])

        return Response(RelationLabelSerializer(relation).data)

    def delete(self, request, label_list_id: int, relation_id: int):
        try:
            relation = RelationLabel.objects.get(id=relation_id, label_list_id=label_list_id)
        except RelationLabel.DoesNotExist:
            return Response(
                {"detail": "Relation label not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        relation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ================================================
# Ontology views
# ================================================

class OntologyListView(APIView):
    """
    List ontologies and save their enabled state.
    This allows the user to enable or disable multiple ontologies at once.

    Input:
        request: The HTTP request object
    Returns:
        A Response object with the list of ontologies and the enabled state
    """

    def get(self, request):
        # Get all ontologies ordered by source (default first) and name
        ontologies = Ontology.objects.all().order_by("-source", "name")
        return Response(OntologySerializer(ontologies, many=True).data)

    def patch(self, request):
        payload = request.data or {}
        ids_enabled = payload.get("ids_enabled")
        if not isinstance(ids_enabled, list):
            return Response(
                {"detail": "`ids_enabled` must be an array of ontology IDs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure that the ids_enabled is a list of integers
        try:
            enabled_set = {int(value) for value in ids_enabled}
        except (TypeError, ValueError):
            return Response(
                {"detail": "`ids_enabled` must contain integer IDs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            Ontology.objects.filter(id__in=enabled_set).update(is_enabled=True)
            Ontology.objects.exclude(id__in=enabled_set).update(is_enabled=False)

        # Return the list of ontologies with the updated enabled state
        return Response(
            OntologySerializer(
                Ontology.objects.all().order_by("-source", "name"), many=True
            ).data
        )


class OntologyUploadView(APIView):
    """
    Upload a .txt ontology file as a custom ontology.
    This allows the user to upload a .txt file to be used as an ontology.
    Expects each line to be a single term (see load_ontology_terms() in generate_triples.py).

    Input:
        request: The HTTP request object
    Returns:
        A Response object with the created ontology and the name of the uploaded file
    """
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "Expected multipart field `file`."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Ensure that the uploaded file is a .txt file
        if not upload.name.lower().endswith(".txt"):
            return Response(
                {"detail": "Only `.txt` files are supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        requested_name = request.data.get("name") or clean_filename_stem(upload.name)
        name = requested_name
        suffix = 2
        # If the name is already taken, add a suffix to make it unique
        while Ontology.objects.filter(name=name).exists():
            name = f"{requested_name}_{suffix}"
            suffix += 1

        ontology = Ontology.objects.create(
            name=name,
            source=SETTINGS_SOURCE_CUSTOM,
            is_enabled=True,
            file=upload,
        )
        return Response(OntologySerializer(ontology).data, status=status.HTTP_201_CREATED)


class OntologyDetailView(APIView):
    """
    Delete a single ontology.
    
    Input:
        request: The HTTP request object
        ontology_id: The ID of the ontology to delete
    Returns:
        A Response object with the deleted ontology
    """
    def delete(self, request, ontology_id: int):
        try:
            ontology = Ontology.objects.get(id=ontology_id)
        except Ontology.DoesNotExist:
            return Response({"detail": "Ontology not found."}, status=status.HTTP_404_NOT_FOUND)

        # Default ontologies cannot be deleted
        if ontology.source == SETTINGS_SOURCE_DEFAULT:
            return Response(
                {"detail": "Default ontologies cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Clean up the uploaded file from disk if present
        if ontology.file:
            try:
                ontology.file.delete(save=False)
            except Exception:
                pass

        ontology.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ================================================
# Summary view (toolbar status chips)
# ================================================


class SettingsSummaryView(APIView):
    """
    Get the summary of the settings panel.

    Input:
        request: The HTTP request object
    Returns:
        A Response object with the summary of the settings panel
    """
    def get(self, request):
        active = LabelList.objects.filter(is_active=True).first()
        active_payload = (
            {"id": active.id, "name": active.name} if active is not None else None
        )
        # The summary consists of:
        # - The active label list name (if any)
        # - The number of enabled ontologies
        # - The number of enabled custom blacklists
        return Response(
            {
                "active_label_list": active_payload,
                "enabled_ontology_count": Ontology.objects.filter(is_enabled=True).count(),
                "enabled_custom_blacklist_count": Blacklist.objects.filter(
                    is_enabled=True, is_default=False
                ).count(),
            }
        )