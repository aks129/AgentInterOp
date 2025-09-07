#!/usr/bin/env python3
"""
Comprehensive MCP Protocol Testing Script

This script tests the MCP (Model Context Protocol) endpoints with real BCSE payloads
and validates error handling, edge cases, and functionality.
"""
import requests
import json
import base64
import time
import sys
from typing import Dict, Any, List


class MCPTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.test_results = []
        
    def log(self, test_name: str, status: str, message: str = "", details: Dict = None):
        """Log test results"""
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "details": details or {},
            "timestamp": time.time()
        }
        self.test_results.append(result)
        print(f"[{status.upper()}] {test_name}: {message}")
        if details:
            print(f"  Details: {json.dumps(details, indent=2)}")
    
    def test_server_health(self):
        """Test if server is running"""
        try:
            response = self.session.get(f"{self.base_url}/healthz", timeout=5)
            if response.status_code == 200:
                self.log("server_health", "pass", "Server is healthy")
                return True
            else:
                self.log("server_health", "fail", f"Server returned {response.status_code}")
                return False
        except Exception as e:
            self.log("server_health", "fail", f"Could not connect to server: {e}")
            return False
    
    def test_begin_chat_thread(self):
        """Test MCP begin_chat_thread endpoint"""
        try:
            url = f"{self.base_url}/api/mcp/begin_chat_thread"
            payload = {}
            
            response = self.session.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                if "content" in data and isinstance(data["content"], list):
                    if len(data["content"]) > 0 and "text" in data["content"][0]:
                        response_text = data["content"][0]["text"]
                        try:
                            parsed_response = json.loads(response_text)
                            if "conversationId" in parsed_response:
                                conversation_id = parsed_response["conversationId"]
                                self.log("begin_chat_thread", "pass", 
                                       f"Successfully created conversation: {conversation_id}",
                                       {"conversation_id": conversation_id, "response": data})
                                return conversation_id
                        except json.JSONDecodeError:
                            pass
                
                self.log("begin_chat_thread", "fail", "Invalid response format", {"response": data})
                return None
            else:
                self.log("begin_chat_thread", "fail", 
                       f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log("begin_chat_thread", "error", f"Exception: {e}")
            return None
    
    def create_bcse_test_payload(self) -> Dict[str, Any]:
        """Create a realistic BCSE test payload"""
        # Patient FHIR data
        patient_data = {
            "resourceType": "Patient",
            "id": "patient-123",
            "gender": "female",
            "birthDate": "1969-01-15"
        }
        
        # Procedure data (mammogram)
        procedure_data = {
            "resourceType": "Procedure",
            "id": "procedure-456",
            "status": "completed",
            "code": {
                "coding": [{
                    "system": "http://www.ama-assn.org/go/cpt",
                    "code": "77067",
                    "display": "Screening mammography, bilateral"
                }]
            },
            "performedDateTime": "2023-08-20",
            "subject": {"reference": "Patient/patient-123"}
        }
        
        # Create FHIR Bundle
        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "entry": [
                {"resource": patient_data},
                {"resource": procedure_data}
            ]
        }
        
        return {
            "conversationId": "",  # Will be filled in
            "message": "I need to check my eligibility for breast cancer screening. I am a 55-year-old female, born on 1969-01-15, and my last mammogram was on 2023-08-20. Please evaluate my eligibility.",
            "attachments": [{
                "name": "patient_bundle.json",
                "contentType": "application/fhir+json",
                "content": base64.b64encode(json.dumps(bundle).encode()).decode(),
                "summary": "FHIR Bundle containing patient demographics and screening history"
            }]
        }
    
    def test_send_message_with_bcse_payload(self, conversation_id: str):
        """Test MCP send_message_to_chat_thread with real BCSE payload"""
        try:
            url = f"{self.base_url}/api/mcp/send_message_to_chat_thread"
            payload = self.create_bcse_test_payload()
            payload["conversationId"] = conversation_id
            
            response = self.session.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                if "content" in data and isinstance(data["content"], list):
                    if len(data["content"]) > 0 and "text" in data["content"][0]:
                        response_text = data["content"][0]["text"]
                        try:
                            parsed_response = json.loads(response_text)
                            if "guidance" in parsed_response and "status" in parsed_response:
                                self.log("send_message_bcse", "pass", 
                                       f"Message processed: {parsed_response['status']}",
                                       {"guidance": parsed_response["guidance"], 
                                        "status": parsed_response["status"],
                                        "response": data})
                                return True
                        except json.JSONDecodeError:
                            pass
                
                self.log("send_message_bcse", "fail", "Invalid response format", {"response": data})
                return False
            else:
                self.log("send_message_bcse", "fail", 
                       f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log("send_message_bcse", "error", f"Exception: {e}")
            return False
    
    def test_check_replies(self, conversation_id: str):
        """Test MCP check_replies endpoint"""
        try:
            url = f"{self.base_url}/api/mcp/check_replies"
            payload = {"conversationId": conversation_id}
            
            response = self.session.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                if "content" in data and isinstance(data["content"], list):
                    if len(data["content"]) > 0 and "text" in data["content"][0]:
                        response_text = data["content"][0]["text"]
                        try:
                            parsed_response = json.loads(response_text)
                            required_fields = ["messages", "guidance", "status", "conversation_ended"]
                            if all(field in parsed_response for field in required_fields):
                                self.log("check_replies", "pass", 
                                       f"Found {len(parsed_response['messages'])} messages",
                                       {"messages_count": len(parsed_response["messages"]),
                                        "status": parsed_response["status"],
                                        "conversation_ended": parsed_response["conversation_ended"],
                                        "response": parsed_response})
                                return True
                        except json.JSONDecodeError:
                            pass
                
                self.log("check_replies", "fail", "Invalid response format", {"response": data})
                return False
            else:
                self.log("check_replies", "fail", 
                       f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log("check_replies", "error", f"Exception: {e}")
            return False
    
    def test_error_handling(self):
        """Test various error conditions"""
        
        # Test 1: Invalid conversation ID for send_message
        try:
            url = f"{self.base_url}/api/mcp/send_message_to_chat_thread"
            payload = {
                "conversationId": "invalid-id-12345",
                "message": "Test message"
            }
            
            response = self.session.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data["content"][0]["text"]
                if "error" in response_text.lower():
                    self.log("error_invalid_conversation", "pass", 
                           "Correctly handled invalid conversation ID")
                else:
                    self.log("error_invalid_conversation", "fail", 
                           "Did not return error for invalid conversation ID")
            else:
                self.log("error_invalid_conversation", "fail", 
                       f"Unexpected HTTP status: {response.status_code}")
        except Exception as e:
            self.log("error_invalid_conversation", "error", f"Exception: {e}")
        
        # Test 2: Invalid conversation ID for check_replies
        try:
            url = f"{self.base_url}/api/mcp/check_replies"
            payload = {"conversationId": "invalid-id-67890"}
            
            response = self.session.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data["content"][0]["text"]
                if "error" in response_text.lower():
                    self.log("error_invalid_check_replies", "pass", 
                           "Correctly handled invalid conversation ID for check_replies")
                else:
                    self.log("error_invalid_check_replies", "fail", 
                           "Did not return error for invalid conversation ID")
            else:
                self.log("error_invalid_check_replies", "fail", 
                       f"Unexpected HTTP status: {response.status_code}")
        except Exception as e:
            self.log("error_invalid_check_replies", "error", f"Exception: {e}")
        
        # Test 3: Malformed JSON
        try:
            url = f"{self.base_url}/api/mcp/begin_chat_thread"
            response = self.session.post(url, data="invalid json", 
                                       headers={"Content-Type": "application/json"}, 
                                       timeout=10)
            
            if response.status_code in [400, 422]:
                self.log("error_malformed_json", "pass", 
                       f"Correctly rejected malformed JSON with HTTP {response.status_code}")
            else:
                self.log("error_malformed_json", "fail", 
                       f"Unexpected response to malformed JSON: {response.status_code}")
        except Exception as e:
            self.log("error_malformed_json", "error", f"Exception: {e}")
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        
        # Test 1: Empty message
        conversation_id = self.test_begin_chat_thread()
        if conversation_id:
            try:
                url = f"{self.base_url}/api/mcp/send_message_to_chat_thread"
                payload = {
                    "conversationId": conversation_id,
                    "message": ""
                }
                
                response = self.session.post(url, json=payload, timeout=10)
                
                if response.status_code == 200:
                    self.log("edge_empty_message", "pass", 
                           "Handled empty message gracefully")
                else:
                    self.log("edge_empty_message", "fail", 
                           f"Failed to handle empty message: {response.status_code}")
            except Exception as e:
                self.log("edge_empty_message", "error", f"Exception: {e}")
        
        # Test 2: Large message
        if conversation_id:
            try:
                large_message = "A" * 10000  # 10KB message
                url = f"{self.base_url}/api/mcp/send_message_to_chat_thread"
                payload = {
                    "conversationId": conversation_id,
                    "message": large_message
                }
                
                response = self.session.post(url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    self.log("edge_large_message", "pass", 
                           "Handled large message gracefully")
                else:
                    self.log("edge_large_message", "fail", 
                           f"Failed to handle large message: {response.status_code}")
            except Exception as e:
                self.log("edge_large_message", "error", f"Exception: {e}")
        
        # Test 3: Wait time in check_replies
        if conversation_id:
            try:
                url = f"{self.base_url}/api/mcp/check_replies"
                payload = {
                    "conversationId": conversation_id,
                    "waitMs": 1000  # 1 second wait
                }
                
                start_time = time.time()
                response = self.session.post(url, json=payload, timeout=10)
                end_time = time.time()
                
                if response.status_code == 200:
                    wait_time = end_time - start_time
                    if wait_time >= 1.0:  # Should wait at least 1 second
                        self.log("edge_wait_time", "pass", 
                               f"Correctly waited {wait_time:.2f} seconds")
                    else:
                        self.log("edge_wait_time", "partial", 
                               f"Wait time was {wait_time:.2f} seconds, expected >= 1.0")
                else:
                    self.log("edge_wait_time", "fail", 
                           f"Failed with waitMs parameter: {response.status_code}")
            except Exception as e:
                self.log("edge_wait_time", "error", f"Exception: {e}")
    
    def run_all_tests(self):
        """Run the complete test suite"""
        print("Starting MCP Protocol Comprehensive Test Suite")
        print("=" * 60)
        
        # Check server health first
        if not self.test_server_health():
            print("Server health check failed. Cannot proceed with tests.")
            return False
        
        # Test basic functionality
        conversation_id = self.test_begin_chat_thread()
        if not conversation_id:
            print("Failed to begin chat thread. Cannot proceed with dependent tests.")
            return False
        
        # Test message sending with BCSE payload
        self.test_send_message_with_bcse_payload(conversation_id)
        
        # Test check replies
        self.test_check_replies(conversation_id)
        
        # Test error handling
        self.test_error_handling()
        
        # Test edge cases
        self.test_edge_cases()
        
        # Print summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        pass_count = sum(1 for r in self.test_results if r["status"] == "pass")
        fail_count = sum(1 for r in self.test_results if r["status"] == "fail")
        error_count = sum(1 for r in self.test_results if r["status"] == "error")
        partial_count = sum(1 for r in self.test_results if r["status"] == "partial")
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {pass_count}")
        print(f"Failed: {fail_count}")
        print(f"Errors: {error_count}")
        print(f"Partial: {partial_count}")
        
        if fail_count > 0 or error_count > 0:
            print("\nFailed/Error Tests:")
            for result in self.test_results:
                if result["status"] in ["fail", "error"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        return fail_count == 0 and error_count == 0


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test MCP Protocol endpoints")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Base URL of the server (default: http://localhost:8000)")
    parser.add_argument("--output", help="Output file for test results (JSON)")
    
    args = parser.parse_args()
    
    tester = MCPTester(args.url)
    success = tester.run_all_tests()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(tester.test_results, f, indent=2)
        print(f"\nTest results saved to: {args.output}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()