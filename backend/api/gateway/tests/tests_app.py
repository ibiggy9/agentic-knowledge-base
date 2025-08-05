import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json
from AgenticAiCore.MCPClient.app import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_load_mcp_client():
    with patch('AgenticAiCore.MCPClient.app.load_mcp_client') as mock_load:
        client_instance = AsyncMock()
        
        client_instance.session = AsyncMock()
        tools_response = MagicMock()
        tools_response.tools = [MagicMock(), MagicMock()]
        tools_response.tools[0].name = "tool1"
        tools_response.tools[1].name = "tool2"
        client_instance.session.list_tools = AsyncMock(return_value=tools_response)
        
        client_instance.process_query = AsyncMock(return_value="Test response")
        client_instance.cleanup = AsyncMock()
        
        mock_load.return_value = client_instance
        
        yield mock_load

def test_get_server_types(client):
    response = client.get("/api/server-types")
    assert response.status_code == 200
    data = response.json()
    assert "server_types" in data
    assert len(data["server_types"]) == 3
    assert all(key in data["server_types"][0] for key in ["id", "name", "description"])

def test_initialize_session(client, mock_load_mcp_client):
    response = client.post(
        "/api/init",
        json={"server_type": "rfx"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    
    response_data = json.loads(data["response"])
    assert "session_id" in response_data
    assert "available_tools" in response_data
    assert response_data["server_type"] == "rfx"
    assert len(response_data["available_tools"]) == 2

def test_query_endpoint(client, mock_load_mcp_client):
    init_response = client.post(
        "/api/init",
        json={"server_type": "rfx"}
    )
    session_id = json.loads(init_response.json()["response"])["session_id"]
    
    response = client.post(
        "/api/query",
        json={
            "session_id": session_id,
            "query": "test query"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["response"] == "Test response"

def test_invalid_session_query(client):
    response = client.post(
        "/api/query",
        json={
            "session_id": "invalid_session_id",
            "query": "test query"
        }
    )
    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]

def test_delete_session(client, mock_load_mcp_client):
    init_response = client.post(
        "/api/init",
        json={"server_type": "rfx"}
    )
    session_id = json.loads(init_response.json()["response"])["session_id"]
    
    response = client.delete(f"/api/session/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Session deleted" in data["message"]

def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
