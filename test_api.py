#!/usr/bin/env python3
"""
Test script for Mobile Dialer Asterisk API
Provides examples and validation for all API endpoints
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "your-secure-api-key"
DEV_API_KEY = "dev-api-key"

def make_request(method: str, endpoint: str, headers: Dict[str, str] = None, data: Dict[str, Any] = None) -> requests.Response:
    """Make HTTP request with error handling"""
    url = f"{BASE_URL}{endpoint}"
    
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=default_headers, params=data)
        elif method.upper() == "POST":
            response = requests.post(url, headers=default_headers, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=default_headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return response
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

def test_health_check():
    """Test health check endpoint"""
    print("Testing health check...")
    response = make_request("GET", "/health")
    
    if response and response.status_code == 200:
        print("✅ Health check passed")
        print(f"Response: {response.json()}")
    else:
        print("❌ Health check failed")
        if response:
            print(f"Status: {response.status_code}, Response: {response.text}")
    print()

def test_check_connection_without_mock():
    """Test connection check without mock data"""
    print("Testing connection check (no mock)...")
    
    headers = {"X-API-Key": API_KEY}
    params = {
        "dialed_number": "1234567890",
        "caller_id": "0987654321"
    }
    
    response = make_request("GET", "/check-connection", headers=headers, data=params)
    
    if response and response.status_code == 200:
        result = response.json()
        print("✅ Connection check successful")
        print(f"Connected: {result.get('connected')}")
        print(f"Message: {result.get('message')}")
        print(f"Channel ID: {result.get('channel_id')}")
    else:
        print("❌ Connection check failed")
        if response:
            print(f"Status: {response.status_code}, Response: {response.text}")
    print()

def test_mock_operations():
    """Test mock operations for debugging"""
    print("Testing mock operations...")
    
    # Add mock numbers
    print("1. Adding mock numbers...")
    headers = {"X-API-Key": DEV_API_KEY}
    mock_data = {
        "numbers": ["1234567890", "555-0100:555-0105", "9876543210"]
    }
    
    response = make_request("POST", "/mock-connect", headers=headers, data=mock_data)
    
    if response and response.status_code == 200:
        result = response.json()
        print("✅ Mock numbers added successfully")
        print(f"Message: {result.get('message')}")
        print(f"Numbers added: {result.get('numbers_added')}")
    else:
        print("❌ Failed to add mock numbers")
        if response:
            print(f"Status: {response.status_code}, Response: {response.text}")
        return
    
    # Check mock status
    print("\n2. Checking mock status...")
    response = make_request("GET", "/mock-status", headers=headers)
    
    if response and response.status_code == 200:
        result = response.json()
        print("✅ Mock status retrieved")
        print(f"Active mocks: {result.get('total_count')}")
        for mock in result.get('active_mocks', []):
            print(f"  - {mock.get('number')} (expires: {mock.get('expires_at')})")
    else:
        print("❌ Failed to get mock status")
        if response:
            print(f"Status: {response.status_code}, Response: {response.text}")
    
    # Test connection with mock
    print("\n3. Testing connection with mock number...")
    headers_api = {"X-API-Key": API_KEY}
    params = {
        "dialed_number": "1234567890",
        "caller_id": "0987654321"
    }
    
    response = make_request("GET", "/check-connection", headers=headers_api, data=params)
    
    if response and response.status_code == 200:
        result = response.json()
        print("✅ Mock connection check successful")
        print(f"Connected: {result.get('connected')}")
        print(f"Channel ID: {result.get('channel_id')}")
        print(f"Message: {result.get('message')}")
        
        # Test disconnect with mock channel
        if result.get('channel_id'):
            print("\n4. Testing disconnect with mock channel...")
            disconnect_data = {"channel_id": result.get('channel_id')}
            response = make_request("POST", "/disconnect-call", headers=headers_api, data=disconnect_data)
            
            if response and response.status_code == 200:
                result = response.json()
                print("✅ Mock disconnect successful")
                print(f"Message: {result.get('message')}")
            else:
                print("❌ Mock disconnect failed")
                if response:
                    print(f"Status: {response.status_code}, Response: {response.text}")
    else:
        print("❌ Mock connection check failed")
        if response:
            print(f"Status: {response.status_code}, Response: {response.text}")
    
    # Clear mocks
    print("\n5. Clearing all mocks...")
    response = make_request("DELETE", "/clear-mocks", headers=headers)
    
    if response and response.status_code == 200:
        result = response.json()
        print("✅ Mocks cleared successfully")
        print(f"Cleared count: {result.get('cleared_count')}")
    else:
        print("❌ Failed to clear mocks")
        if response:
            print(f"Status: {response.status_code}, Response: {response.text}")
    
    print()

def test_authentication():
    """Test API authentication"""
    print("Testing authentication...")
    
    # Test with invalid API key
    print("1. Testing with invalid API key...")
    headers = {"X-API-Key": "invalid-key"}
    params = {"dialed_number": "1234567890"}
    
    response = make_request("GET", "/check-connection", headers=headers, data=params)
    
    if response and response.status_code == 401:
        print("✅ Authentication properly rejected invalid key")
    else:
        print("❌ Authentication test failed")
        if response:
            print(f"Status: {response.status_code}, Response: {response.text}")
    
    # Test without API key
    print("\n2. Testing without API key...")
    response = make_request("GET", "/check-connection", data=params)
    
    if response and response.status_code == 422:  # FastAPI returns 422 for missing headers
        print("✅ Authentication properly requires API key")
    else:
        print("❌ Authentication test failed")
        if response:
            print(f"Status: {response.status_code}, Response: {response.text}")
    
    print()

def test_number_range_parsing():
    """Test number range parsing in mock mode"""
    print("Testing number range parsing...")
    
    headers = {"X-API-Key": DEV_API_KEY}
    mock_data = {
        "numbers": [
            "1234567890",           # Single number
            "555-0100:555-0103",    # Range with dashes
            "5550200:5550202"       # Range without dashes
        ]
    }
    
    response = make_request("POST", "/mock-connect", headers=headers, data=mock_data)
    
    if response and response.status_code == 200:
        result = response.json()
        print("✅ Range parsing successful")
        print(f"Numbers added: {result.get('numbers_added')}")
        
        # Verify specific numbers from ranges
        test_numbers = ["5550100", "5550101", "5550102", "5550103", "5550200", "5550201", "5550202"]
        
        headers_api = {"X-API-Key": API_KEY}
        for number in test_numbers:
            params = {"dialed_number": number}
            response = make_request("GET", "/check-connection", headers=headers_api, data=params)
            
            if response and response.status_code == 200:
                result = response.json()
                if result.get('connected'):
                    print(f"  ✅ {number} found in mock store")
                else:
                    print(f"  ❌ {number} not found in mock store")
        
        # Clear mocks
        make_request("DELETE", "/clear-mocks", headers=headers)
    else:
        print("❌ Range parsing failed")
        if response:
            print(f"Status: {response.status_code}, Response: {response.text}")
    
    print()

def main():
    """Run all tests"""
    print("🚀 Starting Mobile Dialer API Tests\n")
    print("=" * 50)
    
    # Basic tests
    test_health_check()
    test_authentication()
    
    # Functional tests
    test_check_connection_without_mock()
    test_mock_operations()
    test_number_range_parsing()
    
    print("=" * 50)
    print("🏁 Tests completed!")
    print("\nNote: For full testing, ensure the API server is running:")
    print("  docker-compose up -d")
    print("  or")
    print("  uvicorn main:app --host 0.0.0.0 --port 8000")

if __name__ == "__main__":
    main()

