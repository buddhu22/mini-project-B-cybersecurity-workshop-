import pytest

from validators import validate_resource


def payload(url="https://example.org/resource"):
    return {"session_title": "Session", "day": "Day 1", "resource_type": "PDF", "description": "Description", "url": url, "prerequisite": "Python"}


def test_empty_required_fields_rejected():
    values = payload()
    values["description"] = "  "
    _, _, errors = validate_resource(values)
    assert "description" in errors


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///etc/passwd", "data:text/html,hello", "ftp://example.org", "vbscript:msgbox(1)", "not a url"])
def test_rejects_unsafe_or_invalid_urls(url):
    _, _, errors = validate_resource(payload(url))
    assert "url" in errors


def test_http_https_and_known_local_file_urls_are_allowed():
    for url in ("http://example.org", "https://example.org/a", "/provided-resources/11. Flask in Python.pdf"):
        _, _, errors = validate_resource(payload(url))
        assert "url" not in errors


def test_rejects_unlisted_local_path_and_enforces_length():
    _, _, errors = validate_resource(payload("/provided-resources/../../app.py"))
    assert "url" in errors
    values = payload()
    values["prerequisite"] = "x" * 501
    _, _, errors = validate_resource(values)
    assert "prerequisite" in errors
