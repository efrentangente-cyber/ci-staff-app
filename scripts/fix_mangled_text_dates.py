"""
One-off repair: text values like 'Ma-17-e,' or 'Ap-19-n,' -> ISO date 'YYYY-MM-DD'.

- "Ma" / "Ap" are treated as truncated Mar / Apr (from common bad exports).
- Year defaults to --year (or current year) when the string has no year.
- Run from project root:  python scripts/fix_mangled_text_dates.py --dry-run
  then:                  python scripts/fix_mangled_text_dates.py --fix

Env: same as the app (SQLITE_DATABASE or DATABASE_URL for PostgreSQL).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, datetime

# Project root on path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Month token (lower) -> month number. Two-letter forms match truncated English abbrevs.
_MONTH_TOKEN = {
    "jan": 1,
    "ja": 1,
    "feb": 2,
    "fe": 2,
    "mar": 3,
    "ma": 3,  # truncated "Mar"; if you need May, use "may" or "my" per rows below
    "apr": 4,
    "ap": 4,
    "may": 5,
    "my": 5,
    "jun": 6,
    "jn": 6,
    "ju": 6,  # ambiguous vs Jul; prefer 3+ letter keys when possible
    "jul": 7,
    "jl": 7,
    "aug": 8,
    "au": 8,
    "sep": 9,
    "se": 9,
    "oct": 10,
    "oc": 10,
    "nov": 11,
    "no": 11,
    "dec": 12,
    "de": 12,
}

# Patterns: "Ma-17-e", "Ap-19-n", "Mar-17", with optional trailing comma
_MANGLED = re.compile(
    r"^\s*([A-Za-z]{2,9})\s*-\s*(\d{1,2})(?:\s*-\s*[A-Za-z]\s*)?,?\s*$"
)


def parse_mangled_date_string(raw: str, default_year: int) -> str | None:
    """
    Return 'YYYY-MM-DD' if the value matches the broken export pattern, else None.
    """
    if raw is None or not str(raw).strip():
        return None
    s = str(raw).strip()
    m = _MANGLED.match(s)
    if not m:
        return None
    mon_tok = m.group(1).lower()
    day = int(m.group(2))
    if not (1 <= day <= 31):
        return None
    mon = _MONTH_TOKEN.get(mon_tok)
    if mon is None:
        return None
    try:
        d = date(default_year, mon, day)
    except ValueError:
        return None
    return d.isoformat()


def _sqlite_columns(conn, table: str) -> list[tuple[str, str]]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    out = []
    for row in cur.fetchall():
        # Row: cid, name, type, notnull, dflt_value, pk
        name, typ = row[1], (row[2] or "").upper()
        out.append((name, typ))
    return out


def _pg_columns(conn, table: str) -> list[tuple[str, str]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return [(r[0], (r[1] or "").upper()) for r in cur.fetchall()]


def _is_textish_col(typ: str) -> bool:
    t = typ.upper()
    return any(x in t for x in ("TEXT", "CHAR", "DATE", "TIME"))


def run_sqlite(
    path: str,
    table: str,
    columns: list[str] | None,
    default_year: int,
    dry_run: bool,
) -> int:
    import sqlite3

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    all_cols = _sqlite_columns(conn, table)
    text_cols = [c for c, t in all_cols if _is_textish_col(t)]
    if not columns:
        target = text_cols
    else:
        target = [c for c in columns if c in {x[0] for x in all_cols}]
        unknown = set(columns) - set(target)
        if unknown:
            print(f"Unknown columns (skipped): {unknown}")
    if not target:
        print("No columns to scan.")
        conn.close()
        return 0

    id_col = "id" if "id" in {c[0] for c in all_cols} else None
    select_cols = list(dict.fromkeys(([id_col] if id_col else []) + target))
    q = f"SELECT {', '.join(select_cols)} FROM {table}"
    rows = conn.execute(q).fetchall()
    changes = 0
    for row in rows:
        rowd = {k: row[k] for k in row.keys()}
        rid = rowd.get("id")
        for col in target:
            val = rowd.get(col)
            if val is None:
                continue
            newd = parse_mangled_date_string(str(val), default_year)
            if not newd:
                continue
            if str(val).strip().replace(",", "") == newd:
                continue
            changes += 1
            msg = f"  {table}.{col} id={rid}  '{val}' -> '{newd}'"
            if dry_run:
                print(msg)
            else:
                print(msg)
                conn.execute(
                    f"UPDATE {table} SET {col} = ? WHERE {id_col} = ?",
                    (newd, rid),
                )
    if not dry_run and changes and id_col:
        conn.commit()
    elif not dry_run and not id_col and changes:
        print("ERROR: no id column; cannot update safely.", file=sys.stderr)
    conn.close()
    return changes


def run_postgres(
    dsn: str,
    table: str,
    columns: list[str] | None,
    default_year: int,
    dry_run: bool,
) -> int:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    if dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
    all_cols = _pg_columns(conn, table)
    text_cols = [c for c, t in all_cols if _is_textish_col(t)]
    if not columns:
        target = text_cols
    else:
        target = [c for c in columns if c in {x[0] for x in all_cols}]

    id_col = "id" if "id" in {c[0] for c in all_cols} else None
    cur = conn.cursor()
    q = f"SELECT {', '.join(dict.fromkeys((([id_col] if id_col else []) + target)))} FROM {table}"
    cur.execute(q)
    rows = cur.fetchall()
    changes = 0
    for rowd in rows:
        rid = rowd.get("id")
        for col in target:
            val = rowd.get(col)
            if val is None:
                continue
            if hasattr(val, "isoformat"):
                sval = str(val)[:10]
            else:
                sval = str(val)
            newd = parse_mangled_date_string(sval, default_year)
            if not newd:
                continue
            if sval.replace(",", "").strip() == newd:
                continue
            changes += 1
            msg = f"  {table}.{col} id={rid}  '{sval}' -> '{newd}'"
            print(msg)
            if not dry_run and id_col:
                cur.execute(
                    f"UPDATE {table} SET {col} = %s WHERE {id_col} = %s",
                    (newd, rid),
                )
    if not dry_run and changes:
        conn.commit()
    cur.close()
    conn.close()
    return changes


def main() -> int:
    ap = argparse.ArgumentParser(description="Fix mangled month-day text dates in DB")
    ap.add_argument("--table", default="loan_applications", help="Table name")
    ap.add_argument(
        "--columns",
        default="",
        help="Comma-separated columns (default: all text-like columns in table)",
    )
    ap.add_argument("--year", type=int, default=0, help="Year when string has no year (default: today)")
    ap.add_argument("--dry-run", action="store_true", help="Only print, do not update")
    ap.add_argument(
        "--fix",
        action="store_true",
        help="Apply updates (otherwise dry-run is implied if neither set)",
    )
    args = ap.parse_args()
    year = args.year or date.today().year
    cols = [c.strip() for c in args.columns.split(",") if c.strip()]

    dry_run = not args.fix
    if not args.fix and not args.dry_run:
        dry_run = True

    db_url = os.getenv("DATABASE_URL", "").strip()
    sql_path = os.getenv("SQLITE_DATABASE", os.path.join(_ROOT, "app.db")).strip()
    n = 0
    print(f"Year for mangled strings without year: {year}")
    print(f"Table: {args.table}  dry_run={dry_run}")

    if db_url.startswith("postgres"):
        n = run_postgres(db_url, args.table, cols or None, year, dry_run)
    else:
        if not os.path.isfile(sql_path):
            print(f"SQLite file not found: {sql_path}", file=sys.stderr)
            return 1
        n = run_sqlite(sql_path, args.table, cols or None, year, dry_run)

    print(f"Done. {'Would change' if dry_run else 'Changed'} {n} cell(s).")
    if dry_run and n and not args.dry_run:
        print("Run with --fix to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
