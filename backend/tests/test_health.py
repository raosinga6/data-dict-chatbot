import pytest


def test_placeholder():
    assert True


@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_has_required_keys(client):
    data = (await client.get("/health")).json()
    assert "status" in data
    assert "checks" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_health_echoes_trace_id(client):
    response = await client.get("/health", headers={"X-Trace-ID": "test-abc-123"})
    assert response.headers.get("X-Trace-ID") == "test-abc-123"


@pytest.mark.asyncio
async def test_health_generates_trace_id_if_missing(client):
    response = await client.get("/health")
    assert "X-Trace-ID" in response.headers
    assert len(response.headers["X-Trace-ID"]) == 36
