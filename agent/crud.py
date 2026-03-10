"""CRUD operations for the classifications database."""

import re as _re
from datetime import datetime, timezone

from agent.db import get_db
from agent.chromadb_sync import sync_module_to_chromadb, remove_module_from_chromadb


def get_module(module_name: str) -> dict:
    """Look up a classification by name (case-insensitive) or by code."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM classifications WHERE lower(name) = lower(?) OR lower(code) = lower(?)",
        (module_name, module_name),
    ).fetchone()
    if row:
        return {
            "found": True,
            "module_name": row["name"],
            "code": row["code"] or "",
            "description": row["description"] or "",
            "created_at": row["created_at"] or "",
            "updated_at": row["updated_at"] or "",
        }
    return {"found": False, "module_name": module_name}


_LIST_LIMIT = 50    # max rows returned to LLM to stay within token limits


def list_modules() -> dict:
    """List classifications in the database (capped at 50; use list_category for a specific prefix)."""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM classifications").fetchone()[0]
    rows = conn.execute(
        "SELECT * FROM classifications ORDER BY code LIMIT ?", (_LIST_LIMIT,)
    ).fetchall()
    modules_list = [
        {
            "module_name": row["name"],
            "code": row["code"] or "",
            "description": row["description"] or "",
        }
        for row in rows
    ]
    result = {"modules": modules_list, "count": total, "returned": len(modules_list)}
    if total > _LIST_LIMIT:
        result["truncated"] = True
        result["hint"] = "Use list_category with a code prefix to query a specific section."
    return result


_RECENT_LIMIT = 20      # max rows returned by list_recent

_CATEGORY_LIMIT = 100   # max rows per category query


def list_recent(n: int = 5) -> dict:
    """Return the N most recently added agent entries, sorted newest first (capped at 20).

    Only returns entries added via the agent (source='agent'), not XLSX-ingested rows.
    Use before delete_module to identify what was just added.
    """
    n = max(1, min(n, _RECENT_LIMIT))
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM classifications WHERE source = 'agent' ORDER BY created_at DESC LIMIT ?",
        (n,),
    ).fetchall()
    entries = [
        {
            "name": row["name"],
            "code": row["code"] or "",
            "description": row["description"] or "",
            "created_at": row["created_at"] or "",
        }
        for row in rows
    ]
    return {"entries": entries, "returned": len(entries), "n": n}


def list_category(category_prefix: str) -> dict:
    """List classifications whose code starts with a given prefix (capped at 100).

    Useful for seeing all entries in a BIM code category (e.g. '04 05 13').
    """
    conn = get_db()
    escaped = (
        category_prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    total = conn.execute(
        "SELECT COUNT(*) FROM classifications WHERE code LIKE ? ESCAPE '\\'",
        (escaped + "%",),
    ).fetchone()[0]
    rows = conn.execute(
        "SELECT * FROM classifications WHERE code LIKE ? ESCAPE '\\' ORDER BY code LIMIT ?",
        (escaped + "%", _CATEGORY_LIMIT),
    ).fetchall()
    entries = [
        {
            "name": row["name"],
            "code": row["code"] or "",
            "description": row["description"] or "",
            "sheet": row["sheet"] or "",
            "source": row["source"] or "",
        }
        for row in rows
    ]
    result = {"entries": entries, "count": total, "returned": len(entries), "prefix": category_prefix}
    if total > _CATEGORY_LIMIT:
        result["truncated"] = True
        result["hint"] = "Use a more specific prefix to narrow results."
    return result


def add_module(module_name: str, code: str, description: str = "") -> dict:
    """Add a new classification entry. Returns error if name or code already exists."""
    conn = get_db()

    # Check for duplicate name
    existing = conn.execute(
        "SELECT name, code FROM classifications WHERE lower(name) = lower(?)",
        (module_name,),
    ).fetchone()
    if existing:
        return {
            "success": False,
            "error": f"Module '{existing['name']}' already exists with code '{existing['code']}'",
        }

    # Check for duplicate code
    code_existing = conn.execute(
        "SELECT name FROM classifications WHERE lower(code) = lower(?)",
        (code,),
    ).fetchone()
    if code_existing:
        return {
            "success": False,
            "error": f"Code '{code}' is already used by module '{code_existing['name']}'",
        }

    now = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute(
            """
            INSERT INTO classifications (code, name, description, source, created_at, updated_at)
            VALUES (?, ?, ?, 'agent', ?, ?)
            """,
            (code or None, module_name, description, now, now),
        )
        sync_module_to_chromadb(module_name, code, description)
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Operation failed: {e}"}
    return {"success": True, "module_name": module_name, "code": code}


def update_module(
    module_name: str, new_code: str = None, new_description: str = None
) -> dict:
    """Update an existing classification's code and/or description."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM classifications WHERE lower(name) = lower(?)",
        (module_name,),
    ).fetchone()
    if not row:
        return {"success": False, "error": f"Module '{module_name}' not found"}

    old_code = row["code"] or ""
    old_description = row["description"] or ""
    updated_code = new_code if new_code is not None else old_code
    updated_description = new_description if new_description is not None else old_description
    now = datetime.now(timezone.utc).isoformat()

    try:
        cursor = conn.execute(
            """
            UPDATE classifications
            SET code = ?, description = ?, updated_at = ?
            WHERE lower(name) = lower(?)
            """,
            (updated_code or None, updated_description, now, module_name),
        )
        if cursor.rowcount == 0:
            conn.rollback()
            return {"success": False, "error": f"Module '{module_name}' not found"}
        sync_module_to_chromadb(row["name"], updated_code, updated_description)
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Operation failed: {e}"}
    return {
        "success": True,
        "module_name": row["name"],
        "old_code": old_code,
        "new_code": updated_code,
        "old_description": old_description,
        "new_description": updated_description,
    }


def _normalize_name_part(s: str) -> str:
    """Uppercase and replace whitespace with underscores for family name parts."""
    return _re.sub(r'\s+', '_', s.strip().upper())


def generate_family_name(
    category: str, type_function: str, adjective: str = "", company: str = ""
) -> dict:
    """Generate a Revit family name using the convention ABBREV_TYPE_ADJECTIVE_COMPANY.

    Looks up the category abbreviation from the 07-Variable Data entries in the DB.
    Returns the generated name without writing anything to the database.
    """
    conn = get_db()
    row = conn.execute(
        "SELECT code FROM classifications WHERE lower(name) = lower(?) AND sheet = '07-Variable Data'",
        (category.strip(),),
    ).fetchone()
    if not row:
        return {
            "success": False,
            "error": (
                f"No abbreviation found for category '{category}'. "
                "Use list_category('ABBREV') to see available categories."
            ),
        }
    parts = [
        row["code"].upper(),
        _normalize_name_part(type_function),
    ]
    if adjective.strip():
        parts.append(_normalize_name_part(adjective))
    if company.strip():
        parts.append(_normalize_name_part(company))
    return {
        "success": True,
        "family_name": "_".join(parts),
        "category": category,
        "abbreviation": row["code"].upper(),
        "type_function": type_function,
        "adjective": adjective,
        "company": company,
    }


def generate_detail_name(
    category: str, type_function: str, adjective: str = "", company: str = ""
) -> dict:
    """Generate a Revit Smart/Dumb detail name using ABBREV_TYPE_ABBREV_ADJECTIVE_COMPANY.

    Both category and type/function are looked up in the 07-Variable Data abbreviation table.
    Returns the generated name without writing anything to the database.
    """
    conn = get_db()
    cat_row = conn.execute(
        "SELECT code FROM classifications WHERE lower(name) = lower(?) AND sheet = '07-Variable Data'",
        (category.strip(),),
    ).fetchone()
    if not cat_row:
        return {
            "success": False,
            "error": (
                f"No abbreviation found for category '{category}'. "
                "Use list_category('ABBREV') to see available categories."
            ),
        }
    type_row = conn.execute(
        "SELECT code FROM classifications WHERE lower(name) = lower(?) AND sheet = '07-Variable Data'",
        (type_function.strip(),),
    ).fetchone()
    if not type_row:
        return {
            "success": False,
            "error": (
                f"No abbreviation found for type/function '{type_function}'. "
                "Use list_category('ABBREV') to see available type abbreviations."
            ),
        }
    parts = [cat_row["code"].upper(), type_row["code"].upper()]
    if adjective.strip():
        parts.append(_normalize_name_part(adjective))
    if company.strip():
        parts.append(_normalize_name_part(company))
    return {
        "success": True,
        "detail_name": "_".join(parts),
        "category": category,
        "type_function": type_function,
        "abbreviation": cat_row["code"].upper(),
        "type_abbreviation": type_row["code"].upper(),
        "adjective": adjective,
        "company": company,
    }


def delete_module(module_name: str) -> dict:
    """Delete a classification entry from the database."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM classifications WHERE lower(name) = lower(?)",
        (module_name,),
    ).fetchone()
    if not row:
        return {"success": False, "error": f"Module '{module_name}' not found"}

    try:
        conn.execute(
            "DELETE FROM classifications WHERE lower(name) = lower(?)",
            (module_name,),
        )
        remove_module_from_chromadb(row["name"])
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Delete failed: {e}"}
    return {"success": True, "module_name": row["name"], "code": row["code"] or ""}
