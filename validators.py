from urllib.parse import urlsplit
from pathlib import Path
import re

RESOURCE_TYPES = ("PDF", "Documentation", "Article", "Video", "Website", "Other")
REVIEW_STATUSES = ("Not Reviewed", "Working", "Needs Review", "Broken")
FIELDS = {
    "session_title": 200, "day": 10, "resource_type": 30,
    "description": 1000, "url": 500, "prerequisite": 500,
}


def validate_resource(form, session_titles=None):
    cleaned = {key: (form.get(key) or "").strip() for key in FIELDS}
    errors = {}
    for key, max_length in FIELDS.items():
        if not cleaned[key]:
            errors[key] = "This field is required."
        elif len(cleaned[key]) > max_length:
            errors[key] = f"Must be {max_length} characters or fewer."
    if cleaned["resource_type"] and cleaned["resource_type"] not in RESOURCE_TYPES:
        errors["resource_type"] = "Choose a supported resource type."
    if cleaned["day"] and cleaned["day"] not in {f"Day {n}" for n in range(1, 7)}:
        errors["day"] = "Choose a valid workshop day."
    if session_titles is not None and cleaned["session_title"] and cleaned["session_title"] not in session_titles:
        errors["session_title"] = "Choose a session from the workshop timetable."
    if cleaned["url"]:
        try:
            value = cleaned["url"]
            if value.startswith("/provided-resources/"):
                filename = value.removeprefix("/provided-resources/")
                if not re.fullmatch(r"[A-Za-z0-9 _().-]+\.(?:pdf|pptx)", filename, re.IGNORECASE):
                    raise ValueError
                resource_dir = Path(__file__).resolve().parent / "resources"
                root_files = {path.name for path in resource_dir.iterdir() if path.is_file()}
                if filename not in root_files:
                    raise ValueError
            else:
                parsed = urlsplit(value)
                if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc or any(ch.isspace() for ch in value):
                    raise ValueError
        except ValueError:
            errors["url"] = "Enter an http:// or https:// URL, or choose a provided local resource file."
    status = (form.get("resource_review_status") or "Not Reviewed").strip()
    if status not in REVIEW_STATUSES:
        errors["resource_review_status"] = "Choose a supported review status."
    return cleaned, status, errors
