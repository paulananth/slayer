"""
Introspects Snowflake schemas via INFORMATION_SCHEMA and returns a flat list
of ColumnRecord dataclasses — one per (schema, table, column) tuple.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from snowconn import SnowConn


@dataclass
class ColumnRecord:
    database: str
    schema: str
    table: str
    table_type: str       # "BASE TABLE" or "VIEW"
    column: str           # physical column name, original case
    datatype: str         # Snowflake type string, e.g. "NUMBER", "DATE", "TEXT"
    ordinal: int
    is_nullable: bool
    is_unique: bool = False
    table_comment: str | None = None
    column_comment: str | None = None


def introspect_schemas(
    conn: SnowConn, database: str, schemas: Sequence[str]
) -> list[ColumnRecord]:
    """Return ColumnRecord list for all tables/views in the named schemas.

    Runs three INFORMATION_SCHEMA queries:
      1. TABLES  — table names, types, row counts, comments
      2. COLUMNS — column names, data types, ordinals, comments
      3. TABLE_CONSTRAINTS + KEY_COLUMN_USAGE — sets is_unique=True
    """
    if not schemas:
        return []

    schema_list = schemas if isinstance(schemas, list) else list(schemas)
    schema_placeholders = ", ".join(f"'{s.upper()}'" for s in schema_list)
    db = database.upper()

    cursor = conn.get_cursor()

    # ── Query 1: tables ───────────────────────────────────────────────────────
    cursor.execute(f"""
        SELECT
            TABLE_CATALOG,
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TYPE,
            COMMENT,
            ROW_COUNT
        FROM {db}.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA IN ({schema_placeholders})
          AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """)
    table_meta: dict[tuple[str, str], dict] = {}
    for row in cursor.fetchall():
        key = (row[1].upper(), row[2].upper())  # (schema, table)
        table_meta[key] = {
            "database": row[0],
            "schema": row[1],
            "table": row[2],
            "table_type": row[3],
            "table_comment": row[4],
            "row_count": row[5],
        }

    if not table_meta:
        return []

    # ── Query 2: columns ──────────────────────────────────────────────────────
    cursor.execute(f"""
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            COLUMN_NAME,
            ORDINAL_POSITION,
            DATA_TYPE,
            IS_NULLABLE,
            COMMENT
        FROM {db}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA IN ({schema_placeholders})
        ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
    """)
    raw_columns: list[tuple] = cursor.fetchall()

    # ── Query 3: unique / primary key columns ─────────────────────────────────
    unique_columns: set[tuple[str, str, str]] = set()
    try:
        cursor.execute(f"""
            SELECT
                kcu.TABLE_SCHEMA,
                kcu.TABLE_NAME,
                kcu.COLUMN_NAME
            FROM {db}.INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN {db}.INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
              ON  tc.CONSTRAINT_CATALOG = kcu.CONSTRAINT_CATALOG
              AND tc.CONSTRAINT_SCHEMA  = kcu.CONSTRAINT_SCHEMA
              AND tc.CONSTRAINT_NAME    = kcu.CONSTRAINT_NAME
            WHERE tc.TABLE_SCHEMA IN ({schema_placeholders})
              AND tc.CONSTRAINT_TYPE IN ('PRIMARY KEY', 'UNIQUE')
        """)
        for row in cursor.fetchall():
            unique_columns.add((row[0].upper(), row[1].upper(), row[2].upper()))
    except Exception:
        # Constraint metadata may be unavailable in some Snowflake editions
        pass

    # ── Assemble ColumnRecord list ────────────────────────────────────────────
    records: list[ColumnRecord] = []
    for row in raw_columns:
        schema_name, table_name, col_name, ordinal, data_type, nullable, col_comment = row
        key = (schema_name.upper(), table_name.upper())
        if key not in table_meta:
            continue
        meta = table_meta[key]
        records.append(
            ColumnRecord(
                database=meta["database"],
                schema=meta["schema"],
                table=meta["table"],
                table_type=meta["table_type"],
                column=col_name,
                datatype=data_type.upper(),
                ordinal=int(ordinal),
                is_nullable=(nullable.upper() == "YES"),
                is_unique=(
                    (schema_name.upper(), table_name.upper(), col_name.upper())
                    in unique_columns
                ),
                table_comment=meta["table_comment"],
                column_comment=col_comment,
            )
        )

    return records
