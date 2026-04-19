from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.schemas import TableInfo, ColumnInfo
from app.models.db import get_db

router = APIRouter()


@router.get("/tables", response_model=list[TableInfo])
async def get_tables(
    schema: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[TableInfo]:
    if schema:
        result = await db.execute(
            text("SELECT schema_name, table_name, description "
                 "FROM dd_tables WHERE LOWER(schema_name) = LOWER(:s) "
                 "ORDER BY schema_name, table_name"),
            {"s": schema},
        )
    else:
        result = await db.execute(
            text("SELECT schema_name, table_name, description "
                 "FROM dd_tables ORDER BY schema_name, table_name")
        )
    rows = result.mappings().all()
    return [TableInfo(**r) for r in rows]


@router.get("/tables/{schema_name}/{table_name}/columns")
async def get_columns(
    schema_name: str,
    table_name: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Columns — filter by table_name only (schema_name ignored if not in data)
    col_result = await db.execute(
        text("""
            SELECT column_name, data_type, description,
                   is_nullable, is_primary_key, is_foreign_key,
                   references_table, references_column
            FROM dd_columns
            WHERE LOWER(table_name) = LOWER(:t)
            ORDER BY column_name
        """),
        {"t": table_name},
    )
    columns = [
        {
            "name":          r["column_name"],
            "data_type":     r["data_type"] or "text",
            "description":   r["description"] or "",
            "is_nullable":   r["is_nullable"],
            "is_pk":         r["is_primary_key"],
            "is_fk":         r["is_foreign_key"],
            "pii":           False,
            "business_name": "",
            "examples":      [],
        }
        for r in col_result.mappings().all()
    ]

    # Joins
    join_result = await db.execute(
        text("""
            SELECT from_column, to_table, to_column, join_type, description
            FROM dd_joins
            WHERE LOWER(from_table) = LOWER(:t)
            ORDER BY to_table
        """),
        {"t": table_name},
    )
    joins = [
        {
            "left_col":    r["from_column"],
            "right_table": r["to_table"],
            "right_col":   r["to_column"],
            "join_type":   r["join_type"] or "INNER",
            "cardinality": "",
        }
        for r in join_result.mappings().all()
    ]

    return {"columns": columns, "joins": joins}


@router.get("/joins")
async def get_joins(
    table_a: str,
    table_b: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        text("""
            SELECT from_schema, from_table, from_column,
                   to_schema, to_table, to_column, join_type, description
            FROM dd_joins
            WHERE (LOWER(from_table) = LOWER(:a) AND LOWER(to_table) = LOWER(:b))
               OR (LOWER(from_table) = LOWER(:b) AND LOWER(to_table) = LOWER(:a))
        """),
        {"a": table_a, "b": table_b},
    )
    return [dict(r) for r in result.mappings().all()]