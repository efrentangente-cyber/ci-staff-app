"""
Loan document storage: optional BLOB in DB (file_data) so images stay viewable
if disk paths break; filesystem copy is still kept for compatibility.
"""
from __future__ import annotations

import mimetypes
import os

from database import get_database_type, get_db

# Cap per file to keep DB size reasonable (PDFs included).
MAX_DOCUMENT_BLOB_BYTES = 50 * 1024 * 1024


def ensure_documents_blob_columns() -> None:
    """Add mime_type + file_data (BLOB/BYTEA) when missing."""
    try:
        conn = get_db()
        db_type = get_database_type()
        if db_type == "sqlite":
            rows = conn.execute("PRAGMA table_info(documents)").fetchall()
            existing = set()
            for row in rows:
                col_name = row["name"] if hasattr(row, "keys") else row[1]
                existing.add(col_name)
            if "mime_type" not in existing:
                conn.execute("ALTER TABLE documents ADD COLUMN mime_type TEXT")
            if "file_data" not in existing:
                conn.execute("ALTER TABLE documents ADD COLUMN file_data BLOB")
        else:
            conn.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type TEXT")
            conn.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_data BYTEA")
        conn.commit()
        conn.close()
        print("✓ documents blob columns ensured")
    except Exception as e:
        print(f"⚠️  documents blob migration warning: {e}")


def mime_type_for_document(filename: str) -> str:
    fn = (filename or "").strip()
    mt, _ = mimetypes.guess_type(fn)
    if not mt and fn:
        low = fn.lower()
        if low.endswith((".jpg", ".jpeg")):
            return "image/jpeg"
        if low.endswith(".png"):
            return "image/png"
        if low.endswith(".gif"):
            return "image/gif"
        if low.endswith(".webp"):
            return "image/webp"
        if low.endswith(".pdf"):
            return "application/pdf"
    return mt or "application/octet-stream"


def _read_file_bytes_for_blob(abs_path: str) -> bytes | None:
    if not abs_path:
        return None
    try:
        if os.path.isfile(abs_path):
            sz = os.path.getsize(abs_path)
            if sz > MAX_DOCUMENT_BLOB_BYTES:
                return None
            with open(abs_path, "rb") as f:
                return f.read()
    except OSError:
        return None
    return None


def insert_loan_document_row(
    conn,
    loan_application_id: int,
    filepath: str,
    file_name: str,
    uploaded_by: int,
) -> None:
    """
    Insert a documents row; also stores bytes in file_data when the file fits.
    filepath: absolute path to saved upload.
    """
    data = _read_file_bytes_for_blob(filepath)
    mt = mime_type_for_document(file_name or filepath or "")
    conn.execute(
        """
        INSERT INTO documents
        (loan_application_id, file_name, file_path, uploaded_by, mime_type, file_data)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            loan_application_id,
            file_name,
            filepath,
            uploaded_by,
            mt,
            data,
        ),
    )


def blob_bytes(doc_row) -> bytes | None:
    """Normalize file_data from a DB row for serving."""
    if not doc_row:
        return None
    try:
        raw = doc_row["file_data"]
    except (KeyError, IndexError, TypeError):
        return None
    if raw is None:
        return None
    if isinstance(raw, memoryview):
        raw = raw.tobytes()
    elif not isinstance(raw, bytes):
        try:
            raw = bytes(raw)
        except Exception:
            return None
    if len(raw) == 0:
        return None
    return raw


def mime_type_from_document_row(doc_row, fallback_name: str = "") -> str:
    try:
        mt = doc_row["mime_type"]
    except (KeyError, IndexError, TypeError):
        mt = None
    if mt:
        return str(mt)
    try:
        fn = (doc_row["file_name"] or "") if doc_row else ""
    except Exception:
        fn = ""
    return mime_type_for_document(fn or fallback_name)
