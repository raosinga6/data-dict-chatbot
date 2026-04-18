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


@router.get("/tables/{schema_name}/{table_name}/columns",
            response_model=list[ColumnInfo])
async def get_columns(
    schema_name: str,
    table_name: str,
    db: AsyncSession = Depends(get_db),
) -> list[ColumnInfo]:
    result = await db.execute(
        text("SELECT schema_name, table_name, column_name, data_type, "
             "description, is_nullable, is_primary_key, is_foreign_key, "
             "references_table, references_column "
             "FROM dd_columns "
             "WHERE LOWER(schema_name) = LOWER(:s) "
             "AND   LOWER(table_name)  = LOWER(:t) "
             "ORDER BY column_name"),
        {"s": schema_name, "t": table_name},
    )
    rows = result.mappings().all()
    return [ColumnInfo(**r) for r in rows]


@router.get("/joins", response_model=list[dict])
async def get_joins(
    table_a: str,
    table_b: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        text("SELECT from_schema, from_table, from_column, "
             "to_schema, to_table, to_column, join_type, description "
             "FROM dd_joins "
             "WHERE (LOWER(from_table) = LOWER(:a) "
             "       AND LOWER(to_table) = LOWER(:b)) "
             "OR    (LOWER(from_table) = LOWER(:b) "
             "       AND LOWER(to_table) = LOWER(:a))"),
        {"a": table_a, "b": table_b},
    )
    return [dict(r) for r in result.mappings().all()]