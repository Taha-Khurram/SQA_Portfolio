"""
Firebase (Firestore + Storage) data layer for the portfolio.

This is the ONLY module that talks to Firebase. Everything else calls the
functions below. If Firebase is not configured (no credentials in the
environment) the app still runs: settings fall back to sensible defaults and
the project list is empty, so the public site never crashes. Admin writes,
however, require a configured Firebase project.
"""

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone

# firebase-admin is optional at import time so the site can boot without it.
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage
    _FIREBASE_IMPORTED = True
except ImportError:  # pragma: no cover - only when dependency missing
    _FIREBASE_IMPORTED = False


# ------------------------------------------------------------------
# Defaults — used when Firestore has no settings doc yet, or when
# Firebase is not configured at all. These match the site's original
# hardcoded values so nothing looks broken on first run.
# ------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "email": "m.tahaofficial007@gmail.com",
    "phone": "+92 331 5604180",
    "linkedin_url": "https://www.linkedin.com/in/muhammad-taha-khurram-2b77ba366/",
    "github_url": "https://github.com/mtahaofficial007-collab",
}

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

_db = None            # Firestore client (lazily created)
_bucket = None        # Storage bucket (lazily created)
_init_attempted = False
_init_error = None


# ------------------------------------------------------------------
# Initialisation
# ------------------------------------------------------------------
def _init():
    """Initialise Firebase once. Safe to call repeatedly."""
    global _db, _bucket, _init_attempted, _init_error

    if _init_attempted:
        return _db is not None

    _init_attempted = True

    if not _FIREBASE_IMPORTED:
        _init_error = "firebase-admin package is not installed."
        return False

    raw = os.getenv("FIREBASE_CREDENTIALS")
    bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")

    if not raw:
        _init_error = "FIREBASE_CREDENTIALS env var is not set."
        return False

    try:
        # FIREBASE_CREDENTIALS may be the JSON string itself or a path to it.
        if os.path.isfile(raw):
            cred = credentials.Certificate(raw)
        else:
            cred = credentials.Certificate(json.loads(raw))

        options = {"storageBucket": bucket_name} if bucket_name else None
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, options)

        _db = firestore.client()
        if bucket_name:
            _bucket = storage.bucket()
        return True
    except Exception as exc:  # pragma: no cover - config errors
        _init_error = f"Firebase init failed: {exc}"
        _db = None
        return False


def is_configured():
    """True when Firestore is reachable (credentials present and valid)."""
    return _init()


def config_error():
    """Human-readable reason Firebase is unavailable, or None."""
    return _init_error


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def slugify(text):
    """Turn a title into a URL-safe slug."""
    text = (text or "").strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "project"


def _unique_slug(base_slug, exclude_id=None):
    """Ensure the slug is unique across the projects collection."""
    if not _init():
        return base_slug
    slug = base_slug
    n = 2
    while True:
        docs = _db.collection("projects").where("slug", "==", slug).stream()
        clash = any(d.id != exclude_id for d in docs)
        if not clash:
            return slug
        slug = f"{base_slug}-{n}"
        n += 1


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------
# Short-lived in-process cache. get_settings() is called on EVERY request
# (via the template context processor), so hitting Firestore each time adds
# network latency to every page. Cache for a few seconds and invalidate on write.
_settings_cache = {"data": None, "ts": 0.0}
_SETTINGS_TTL = 60  # seconds


def get_settings():
    """Return the site settings dict (cached), falling back to defaults."""
    now = time.time()
    if _settings_cache["data"] is not None and now - _settings_cache["ts"] < _SETTINGS_TTL:
        return dict(_settings_cache["data"])

    if not _init():
        return dict(DEFAULT_SETTINGS)
    try:
        doc = _db.collection("settings").document("site").get()
        if doc.exists:
            data = doc.to_dict() or {}
            # Merge over defaults so missing keys are always present.
            merged = {**DEFAULT_SETTINGS, **data}
            _settings_cache["data"] = merged
            _settings_cache["ts"] = now
            return dict(merged)
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def update_settings(data):
    """Persist site settings. Raises if Firebase is not configured."""
    if not _init():
        raise RuntimeError(config_error() or "Firebase is not configured.")
    payload = {
        "email": (data.get("email") or "").strip(),
        "phone": (data.get("phone") or "").strip(),
        "linkedin_url": (data.get("linkedin_url") or "").strip(),
        "github_url": (data.get("github_url") or "").strip(),
    }
    _db.collection("settings").document("site").set(payload, merge=True)
    # Invalidate the cache so the change is reflected immediately.
    _settings_cache["data"] = None
    _settings_cache["ts"] = 0.0
    return payload


# ------------------------------------------------------------------
# Projects
# ------------------------------------------------------------------
def _doc_to_project(doc):
    data = doc.to_dict() or {}
    data["id"] = doc.id
    data.setdefault("tags", [])
    return data


def list_projects():
    """All projects, ordered by `order` then creation time. [] on failure."""
    if not _init():
        return []
    try:
        docs = _db.collection("projects").stream()
        projects = [_doc_to_project(d) for d in docs]
        projects.sort(key=lambda p: (p.get("order", 0), p.get("created_at") or 0))
        return projects
    except Exception:
        return []


def get_project(slug):
    """Fetch one project by slug, or None."""
    if not _init():
        return None
    try:
        docs = list(_db.collection("projects").where("slug", "==", slug).limit(1).stream())
        if docs:
            return _doc_to_project(docs[0])
    except Exception:
        pass
    return None


def get_project_by_id(project_id):
    if not _init():
        return None
    try:
        doc = _db.collection("projects").document(project_id).get()
        if doc.exists:
            return _doc_to_project(doc)
    except Exception:
        pass
    return None


def create_project(data):
    """Create a project. Returns the new id."""
    if not _init():
        raise RuntimeError(config_error() or "Firebase is not configured.")
    payload = _clean_project_payload(data)
    payload["slug"] = _unique_slug(slugify(data.get("slug") or data.get("title")))
    payload["created_at"] = datetime.now(timezone.utc).timestamp()
    ref = _db.collection("projects").document()
    ref.set(payload)
    return ref.id


def update_project(project_id, data):
    if not _init():
        raise RuntimeError(config_error() or "Firebase is not configured.")
    payload = _clean_project_payload(data)
    if data.get("slug") or data.get("title"):
        payload["slug"] = _unique_slug(
            slugify(data.get("slug") or data.get("title")), exclude_id=project_id
        )
    _db.collection("projects").document(project_id).set(payload, merge=True)
    return project_id


def delete_project(project_id):
    if not _init():
        raise RuntimeError(config_error() or "Firebase is not configured.")
    _db.collection("projects").document(project_id).delete()


def _clean_project_payload(data):
    """Whitelist + normalise the fields we store for a project."""
    tags = data.get("tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    payload = {
        "title": (data.get("title") or "").strip(),
        "short_description": (data.get("short_description") or "").strip(),
        "overview": (data.get("overview") or "").strip(),
        "tags": tags or [],
    }
    # Only overwrite images when a new URL was provided (edit keeps old image).
    if data.get("card_image_url"):
        payload["card_image_url"] = data["card_image_url"]
    if data.get("preview_image_url"):
        payload["preview_image_url"] = data["preview_image_url"]
    if data.get("order") is not None:
        try:
            payload["order"] = int(data["order"])
        except (TypeError, ValueError):
            payload["order"] = 0
    return payload


# ------------------------------------------------------------------
# Image upload (Firebase Storage)
# ------------------------------------------------------------------
def allowed_image(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


def upload_image(file_storage):
    """
    Upload a Werkzeug FileStorage to Firebase Storage and return its public URL.
    Returns None if no file was provided. Raises on misconfig / bad file.
    """
    if file_storage is None or not file_storage.filename:
        return None
    if not _init() or _bucket is None:
        raise RuntimeError(
            config_error() or "Firebase Storage bucket is not configured."
        )
    if not allowed_image(file_storage.filename):
        raise ValueError("Unsupported image type.")

    from werkzeug.utils import secure_filename

    safe = secure_filename(file_storage.filename)
    ext = safe.rsplit(".", 1)[1].lower()
    blob_name = f"projects/{uuid.uuid4().hex}.{ext}"
    blob = _bucket.blob(blob_name)
    blob.upload_from_file(file_storage, content_type=file_storage.mimetype)
    blob.make_public()
    return blob.public_url
