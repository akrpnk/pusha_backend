import pytest


@pytest.mark.asyncio
async def test_rate_limit_header(async_client):
    body = {"initData": "anything"}

    res = await async_client.post("/pet", json=body)
    assert res.headers["x-ratelimit-remaining"]
