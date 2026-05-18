import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.tools_service import N8nToolsService, handle_function_call


@pytest.fixture
def service():
    return N8nToolsService({
        "base_url": "http://localhost:5678",
        "webhooks": {
            "web_search": "/webhook/web-search",
            "control_smart_home": "/webhook/smart-home",
        },
        "timeout": 10,
    })


@pytest.mark.asyncio
async def test_execute_tool_success(service):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"result": "search results"})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await service.execute_tool("web_search", {"query": "test"})

    assert result == "search results"


@pytest.mark.asyncio
async def test_execute_tool_missing_webhook(service):
    result = await service.execute_tool("unknown_tool", {})
    assert "No webhook configured" in result


@pytest.mark.asyncio
async def test_execute_tool_http_error(service):
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await service.execute_tool("web_search", {"query": "test"})

    assert "status 500" in result


@pytest.mark.asyncio
async def test_execute_tool_connection_error(service):
    import aiohttp
    mock_session = MagicMock()
    mock_session.post = MagicMock(side_effect=aiohttp.ClientError("connection refused"))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await service.execute_tool("web_search", {"query": "test"})

    assert "could not reach" in result


@pytest.mark.asyncio
async def test_handle_function_call_valid_json():
    svc = N8nToolsService({"base_url": "http://localhost:5678", "webhooks": {}, "timeout": 5})
    result = await handle_function_call(svc, "unknown_tool", '{"query": "hello"}')
    assert "No webhook configured" in result


@pytest.mark.asyncio
async def test_handle_function_call_invalid_json():
    svc = N8nToolsService({"base_url": "http://localhost:5678", "webhooks": {}, "timeout": 5})
    result = await handle_function_call(svc, "web_search", "not json {")
    assert "could not parse" in result


@pytest.mark.asyncio
async def test_handle_function_call_dict_arguments():
    svc = N8nToolsService({"base_url": "http://localhost:5678", "webhooks": {}, "timeout": 5})
    result = await handle_function_call(svc, "unknown_tool", {"query": "hello"})
    assert "No webhook configured" in result
