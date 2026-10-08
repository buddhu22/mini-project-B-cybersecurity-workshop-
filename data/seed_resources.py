"""Seed the authoritative workshop timetable and provided resource PDFs."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from extensions import db
from models import Resource, Session

SESSIONS = [
    ("Day 1", "09:30 AM – 11:30 AM", "Foundation of Modern Web Technologies & Software Architecture Concepts"),
    ("Day 1", "12:00 PM – 02:00 PM", "File Handling Techniques & Python Utility Libraries"),
    ("Day 2", "09:30 AM – 11:30 AM", "Prepare Isolated Environment for Python IDEs and Cyber Security"),
    ("Day 2", "12:00 PM – 02:00 PM", "Responsive Web Interface Architecture"),
    ("Day 3", "09:30 AM – 11:30 AM", "SQL Query Processing & Python-Database Connectivity"),
    ("Day 3", "12:00 PM – 02:00 PM", "Secure Web Application Development using Streamlit Framework"),
    ("Day 4", "09:30 AM – 11:30 AM", "Rapid Web Application Development using Flask"),
    ("Day 4", "12:00 PM – 02:00 PM", "Flask Application Architecture, URL Routing & Request Lifecycle"),
    ("Day 5", "09:30 AM – 11:30 AM", "Mini-Project"),
    ("Day 5", "12:00 PM – 02:00 PM", "Mini-Project"),
    ("Day 6", "09:30 AM – 11:30 AM", "Cybersecurity with AI"),
]

RESOURCE_MAP = [
    (1, "Python Fundamentals_Software Architecture.pptx", "Other", "Provided workshop slides covering Python fundamentals and software architecture.", "Basic computer literacy"),
    (2, "4.Python File Handling.pdf", "PDF", "Provided workshop material on Python file handling.", "Basic Python syntax"),
    (2, "5.Python Libraries.pdf", "PDF", "Provided workshop material on Python utility libraries.", "Basic Python syntax"),
    (3, "6.Virtualization.pdf", "PDF", "Provided material on virtualization and isolated environments.", "Basic computer literacy"),
    (3, "P2.Docker installation.pdf", "PDF", "Provided Docker installation workshop guide.", "Basic command-line familiarity"),
    (5, "7.Database-connectivity.pdf", "PDF", "Provided material on database connectivity with Python.", "Basic SQL and Python"),
    (6, "9.Streamlit with Python.pdf", "PDF", "Provided workshop material on Streamlit with Python.", "Basic Python syntax"),
    (7, "11. Flask in Python.pdf", "PDF", "Provided workshop material on Flask application development.", "Basic Python syntax"),
    (8, "12.Secure Backend Engineering using Flask.pdf", "PDF", "Provided workshop material on secure Flask backend engineering.", "Basic Flask familiarity"),
]


def seed_sessions():
    existing = {(item.day, item.sort_order): item for item in Session.query.all()}
    for index, (day, time_slot, title) in enumerate(SESSIONS, start=1):
        if (day, index) not in existing:
            db.session.add(Session(day=day, time_slot=time_slot, title=title, sort_order=index))
        else:
            item = existing[(day, index)]
            item.day, item.time_slot, item.title = day, time_slot, title
    db.session.commit()


def seed_resources():
    seed_sessions()
    if Resource.query.count():
        return
    base_dir = Path(__file__).resolve().parents[1]
    for index, filename, kind, description, prerequisite in RESOURCE_MAP:
        session_day, time_slot, title = SESSIONS[index - 1]
        path = base_dir / "resources" / filename
        resource_url = f"/provided-resources/{filename}" if path.is_file() else f"https://localhost/resources/{filename}"
        # Provided files are served by Flask from the packaged resource directory; external URLs are never fetched.
        db.session.add(Resource(session_title=title, day=session_day, time_slot=time_slot, resource_type=kind,
                                description=description, url=resource_url, prerequisite=prerequisite))
    db.session.commit()


if __name__ == "__main__":
    from app import app, initialize_database
    with app.app_context():
        initialize_database()
        print(f"Seeded {Session.query.count()} sessions and {Resource.query.count()} resources.")
