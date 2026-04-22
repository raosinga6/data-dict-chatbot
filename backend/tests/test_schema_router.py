import pytest


@pytest.mark.asyncio
async def test_get_tables_returns_list(client):
    response = await client.get("/api/v1/tables")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_tables_has_expected_fields(client):
    response = await client.get("/api/v1/tables")
    assert response.status_code == 200
    first = response.json()[0]
    assert "table_name" in first
    assert "schema_name" in first


@pytest.mark.asyncio
async def test_get_columns_for_known_table(client):
    response = await client.get("/api/v1/tables/sales/orders/columns")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_columns_unknown_table_returns_empty_or_404(client):
    response = await client.get("/api/v1/tables/sales/nonexistent/columns")
    assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_get_joins_returns_list(client):
    response = await client.get("/api/v1/joins?table_a=orders&table_b=customers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


pytestmark = pytest.mark.skipif(
    not __import__("os").getenv("DATABASE_URL"),
    reason="No DATABASE_URL — skipping DB tests in CI"
)