"""
Protocol Integration Tests

Tests A2A JSON-RPC and MCP protocol implementations with real endpoint calls.
"""
import pytest
import json
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app


class TestA2AProtocol:
    """Test A2A JSON-RPC protocol compliance"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
        self.a2a_endpoint = "/api/bridge/bcse/a2a"
    
    def test_message_send_valid_request(self):
        """Test message/send with valid JSON-RPC request"""
        request = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "parts": [{
                        "kind": "text",
                        "text": '{"sex": "female", "birthDate": "1968-05-10", "last_mammogram": "2024-12-01"}'
                    }]
                }
            },
            "id": "test-1"
        }
        
        response = self.client.post(self.a2a_endpoint, json=request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "1"  # Note: endpoint uses "1" as default
        assert "result" in data
        
        result = data["result"]
        assert "id" in result
        assert result["status"]["state"] in ["working", "completed"]
        assert "history" in result
        assert len(result["history"]) >= 1

    def test_message_send_bcse_evaluation(self):
        """Test message/send with BCS-E payload evaluation"""
        request = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "parts": [{
                        "kind": "text",
                        "text": '{"sex": "female", "birthDate": "1968-05-10", "last_mammogram": "2024-12-01"}'
                    }]
                }
            },
            "id": "bcse-test"
        }
        
        response = self.client.post(self.a2a_endpoint, json=request)
        data = response.json()
        
        # Should have agent response with BCS-E decision
        history = data["result"]["history"]
        assert len(history) >= 2  # User message + agent response
        
        agent_message = None
        for msg in history:
            if msg["role"] == "agent":
                agent_message = msg
                break
        
        assert agent_message is not None
        agent_text = agent_message["parts"][0]["text"]
        decision_data = json.loads(agent_text)
        
        assert "status" in decision_data
        assert decision_data["status"] == "eligible"
        assert "rationale" in decision_data

    def test_method_not_found_error(self):
        """Test JSON-RPC method not found error (-32601)"""
        request = {
            "jsonrpc": "2.0",
            "method": "nonexistent/method",
            "params": {},
            "id": "error-test"
        }
        
        response = self.client.post(self.a2a_endpoint, json=request)
        assert response.status_code == 200  # JSON-RPC errors return 200
        
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601
        assert "Method not found" in data["error"]["message"]

    def test_message_stream_sse(self):
        """Test message/stream SSE functionality"""
        request = {
            "jsonrpc": "2.0", 
            "method": "message/stream",
            "params": {},
            "id": "stream-test"
        }
        
        response = self.client.post(self.a2a_endpoint, json=request)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        # Parse SSE events
        events = []
        for line in response.text.split('\n'):
            if line.startswith('data: '):
                try:
                    event_data = json.loads(line[6:])  # Remove 'data: '
                    events.append(event_data)
                except json.JSONDecodeError:
                    continue
        
        assert len(events) >= 2  # Should have multiple events
        
        # Check for final event with final:true
        final_event = None
        for event in events:
            if event.get("result", {}).get("final"):
                final_event = event
                break
        
        assert final_event is not None
        assert final_event["result"]["final"] is True

    def test_tasks_get_nonexistent(self):
        """Test tasks/get with nonexistent task ID"""
        request = {
            "jsonrpc": "2.0",
            "method": "tasks/get", 
            "params": {"id": "nonexistent-task"},
            "id": "get-test"
        }
        
        response = self.client.post(self.a2a_endpoint, json=request)
        data = response.json()
        
        assert "error" in data
        assert data["error"]["code"] == -32001
        assert "Task not found" in data["error"]["message"]

    def test_tasks_cancel(self):
        """Test tasks/cancel functionality"""
        # First create a task
        create_request = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "parts": [{"kind": "text", "text": "test"}]
                }
            },
            "id": "create-task"
        }
        
        create_response = self.client.post(self.a2a_endpoint, json=create_request)
        task_id = create_response.json()["result"]["id"]
        
        # Now cancel the task
        cancel_request = {
            "jsonrpc": "2.0",
            "method": "tasks/cancel",
            "params": {"id": task_id},
            "id": "cancel-test"
        }
        
        response = self.client.post(self.a2a_endpoint, json=cancel_request)
        data = response.json()
        
        assert "result" in data
        assert data["result"]["status"]["state"] == "canceled"

    def test_invalid_json_rpc_format(self):
        """Test handling of invalid JSON-RPC format"""
        invalid_requests = [
            {"method": "test"},  # Missing jsonrpc version
            {"jsonrpc": "1.0", "method": "test", "id": 1},  # Wrong version
            {"jsonrpc": "2.0", "id": 1},  # Missing method
        ]
        
        for invalid_request in invalid_requests:
            response = self.client.post(self.a2a_endpoint, json=invalid_request)
            # Should handle gracefully, either with error response or 400
            assert response.status_code in [200, 400]


class TestMCPProtocol:
    """Test MCP protocol compliance"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
        self.mcp_base = "/api/mcp/bcse"
    
    def test_begin_chat_thread(self):
        """Test MCP begin_chat_thread tool"""
        response = self.client.post(f"{self.mcp_base}/begin_chat_thread", json={})
        assert response.status_code == 200
        
        data = response.json()
        assert "content" in data
        assert len(data["content"]) > 0
        assert data["content"][0]["type"] == "text"
        
        # Parse the response to get conversation ID
        response_text = data["content"][0]["text"]
        response_obj = json.loads(response_text)
        assert "conversationId" in response_obj
        assert response_obj["conversationId"].startswith("bcse-")

    def test_send_message_to_chat_thread(self):
        """Test MCP send_message_to_chat_thread tool"""
        # First begin a chat thread
        begin_response = self.client.post(f"{self.mcp_base}/begin_chat_thread", json={})
        begin_data = begin_response.json()
        conversation_data = json.loads(begin_data["content"][0]["text"])
        conversation_id = conversation_data["conversationId"]
        
        # Send message
        send_request = {
            "conversationId": conversation_id,
            "message": '{"sex": "female", "birthDate": "1968-05-10", "last_mammogram": "2024-12-01"}'
        }
        
        response = self.client.post(f"{self.mcp_base}/send_message_to_chat_thread", json=send_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "guidance" in data
        assert "status" in data
        assert data["status"] in ["working", "input-required", "completed"]

    def test_check_replies(self):
        """Test MCP check_replies tool"""
        # Begin chat and send message first
        begin_response = self.client.post(f"{self.mcp_base}/begin_chat_thread", json={})
        begin_data = begin_response.json()
        conversation_data = json.loads(begin_data["content"][0]["text"])
        conversation_id = conversation_data["conversationId"]
        
        # Check replies
        check_request = {"conversationId": conversation_id}
        response = self.client.post(f"{self.mcp_base}/check_replies", json=check_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "messages" in data
        assert "guidance" in data
        assert "status" in data
        assert "conversation_ended" in data
        
        # Should have administrator message
        assert isinstance(data["messages"], list)
        if data["messages"]:
            msg = data["messages"][0]
            assert msg["from"] == "administrator"
            assert "text" in msg

    def test_mcp_triplet_workflow(self):
        """Test complete MCP workflow: begin → send → check"""
        # Step 1: Begin chat thread
        begin_response = self.client.post(f"{self.mcp_base}/begin_chat_thread", json={})
        begin_data = begin_response.json()
        conversation_data = json.loads(begin_data["content"][0]["text"])
        conversation_id = conversation_data["conversationId"]
        
        # Step 2: Send message
        send_request = {
            "conversationId": conversation_id,
            "message": "Please evaluate BCS-E eligibility"
        }
        send_response = self.client.post(f"{self.mcp_base}/send_message_to_chat_thread", json=send_request)
        assert send_response.status_code == 200
        
        # Step 3: Check replies
        check_request = {"conversationId": conversation_id}
        check_response = self.client.post(f"{self.mcp_base}/check_replies", json=check_request)
        check_data = check_response.json()
        
        assert check_data["status"] == "input-required"
        assert len(check_data["messages"]) > 0
        assert "mammogram" in check_data["messages"][0]["text"].lower()

    def test_mcp_conversation_not_found(self):
        """Test MCP tools with nonexistent conversation ID"""
        nonexistent_id = "nonexistent-conversation"
        
        # Test send_message with bad ID
        send_request = {
            "conversationId": nonexistent_id,
            "message": "test"
        }
        send_response = self.client.post(f"{self.mcp_base}/send_message_to_chat_thread", json=send_request)
        send_data = send_response.json()
        # Should return error in content
        assert "error" in send_data.get("guidance", "").lower() or "error" in str(send_data)
        
        # Test check_replies with bad ID  
        check_request = {"conversationId": nonexistent_id}
        check_response = self.client.post(f"{self.mcp_base}/check_replies", json=check_request)
        check_data = check_response.json()
        assert "error" in str(check_data).lower()

    def test_mcp_wait_functionality(self):
        """Test MCP check_replies with wait parameter"""
        # Begin chat
        begin_response = self.client.post(f"{self.mcp_base}/begin_chat_thread", json={})
        begin_data = begin_response.json()
        conversation_data = json.loads(begin_data["content"][0]["text"])
        conversation_id = conversation_data["conversationId"]
        
        # Check replies with wait time
        import time
        start_time = time.time()
        
        check_request = {
            "conversationId": conversation_id,
            "waitMs": 1000
        }
        response = self.client.post(f"{self.mcp_base}/check_replies", json=check_request)
        
        elapsed_time = time.time() - start_time
        
        # Should have waited approximately the specified time
        # Allow for some variance in timing
        assert elapsed_time >= 0.5  # At least half the wait time
        assert response.status_code == 200


class TestProtocolCompliance:
    """Test protocol compliance requirements"""
    
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_agent_card_discovery(self):
        """Test agent card discovery endpoint"""
        response = self.client.get("/.well-known/agent-card.json")
        assert response.status_code == 200
        
        card = response.json()
        assert card["protocolVersion"] == "0.4.0"
        assert card["preferredTransport"] == "JSONRPC"
        assert card["capabilities"]["streaming"] is True
        assert "skills" in card
        assert "endpoints" in card
        
        # Should have both endpoint types now
        endpoints = card["endpoints"]
        assert "jsonrpc" in endpoints
        assert "bcse_simple" in endpoints

    def test_selftest_endpoint(self):
        """Test selftest endpoint completeness"""
        response = self.client.get("/api/selftest")
        assert response.status_code == 200
        
        data = response.json()
        assert data["ok"] is True
        assert "a2a" in data
        assert "mcp" in data
        assert "scenario" in data
        assert "available_scenarios" in data
        assert "endpoints" in data
        
        # Check required A2A methods
        required_a2a = ["message/send", "message/stream", "tasks/get", "tasks/cancel"]
        for method in required_a2a:
            assert method in data["a2a"]
        
        # Check required MCP tools
        required_mcp = ["begin_chat_thread", "send_message_to_chat_thread", "check_replies"]
        for tool in required_mcp:
            assert tool in data["mcp"]

    def test_health_endpoints(self):
        """Test health check endpoints"""
        # Test /health
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        
        # Test /healthz
        response = self.client.get("/healthz") 
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "ts" in data

    def test_version_endpoint(self):
        """Test version endpoint"""
        response = self.client.get("/version")
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "scenario" in data
        assert data["scenario"] == "bcse"


class TestErrorHandling:
    """Test error handling across protocols"""
    
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_malformed_json_requests(self):
        """Test handling of malformed JSON requests"""
        endpoints = [
            "/api/bridge/bcse/a2a",
            "/api/mcp/bcse/send_message_to_chat_thread"
        ]
        
        for endpoint in endpoints:
            response = self.client.post(endpoint, data="invalid json")
            # Should handle malformed JSON gracefully
            assert response.status_code in [400, 422, 200]  # Various acceptable error responses
    
    def test_oversized_requests(self):
        """Test handling of oversized requests"""
        large_payload = "x" * (10 * 1024 * 1024)  # 10MB payload
        
        request = {
            "jsonrpc": "2.0",
            "method": "message/send", 
            "params": {
                "message": {
                    "parts": [{"kind": "text", "text": large_payload}]
                }
            },
            "id": "oversized-test"
        }
        
        response = self.client.post("/api/bridge/bcse/a2a", json=request)
        # Should handle large requests (may succeed or fail depending on limits)
        assert response.status_code in [200, 413, 422]
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields"""
        # A2A request missing required fields
        incomplete_a2a = {
            "jsonrpc": "2.0",
            "method": "message/send"
            # Missing params and id
        }
        
        response = self.client.post("/api/bridge/bcse/a2a", json=incomplete_a2a)
        # Should handle missing fields gracefully
        assert response.status_code in [200, 400, 422]
        
        # MCP request missing required fields
        incomplete_mcp = {
            "message": "test"
            # Missing conversationId
        }
        
        response = self.client.post("/api/mcp/bcse/send_message_to_chat_thread", json=incomplete_mcp)
        assert response.status_code in [200, 400, 422]