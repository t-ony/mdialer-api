"""
Asterisk API Backend for Mobile Dialer App
Provides endpoints to check call existence on Asterisk server via ARI
"""

import os
import re
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import aiohttp
import requests
from fastapi import FastAPI, HTTPException, Depends, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ASTERISK_ARI_URL = os.getenv("ASTERISK_ARI_URL", "http://localhost:8088/ari")
ASTERISK_ARI_USERNAME = os.getenv("ASTERISK_ARI_USERNAME", "ari_user")
ASTERISK_ARI_PASSWORD = os.getenv("ASTERISK_ARI_PASSWORD", "ari_password")
API_KEY = os.getenv("API_KEY", "your-secure-api-key")
DEV_API_KEY = os.getenv("DEV_API_KEY", "dev-api-key")
MOCK_TIMEOUT_MINUTES = int(os.getenv("MOCK_TIMEOUT_MINUTES", "5"))

# In-memory storage for mock connections
mock_store: Dict[str, Dict[str, Any]] = {}

# Pydantic models
class MockConnectRequest(BaseModel):
    numbers: List[str] = Field(..., description="List of phone numbers or ranges (e.g., ['1234567890', '555-0100:555-0199'])")

class ConnectionResponse(BaseModel):
    connected: bool
    channel_id: Optional[str] = None
    message: str
    timestamp: str

class DisconnectRequest(BaseModel):
    channel_id: str

class MockClearResponse(BaseModel):
    cleared_count: int
    message: str

# Utility functions
def normalize_phone_number(number: str) -> str:
    """Remove all non-digit characters from phone number"""
    return re.sub(r'\D', '', number)

def get_last_digits(number: str, digits: int = 7) -> str:
    """Get last N digits of a phone number"""
    normalized = normalize_phone_number(number)
    return normalized[-digits:] if len(normalized) >= digits else normalized

def parse_number_ranges(numbers: List[str]) -> List[str]:
    """Parse number ranges and expand them to individual numbers"""
    expanded_numbers = []
    
    for item in numbers:
        if ':' in item:
            # Handle range format like "555-0100:555-0199"
            start, end = item.split(':')
            start_normalized = normalize_phone_number(start)
            end_normalized = normalize_phone_number(end)
            
            if len(start_normalized) == len(end_normalized):
                start_num = int(start_normalized)
                end_num = int(end_normalized)
                
                for num in range(start_num, end_num + 1):
                    expanded_numbers.append(str(num).zfill(len(start_normalized)))
            else:
                logger.warning(f"Invalid range format: {item}")
                expanded_numbers.append(normalize_phone_number(item))
        else:
            expanded_numbers.append(normalize_phone_number(item))
    
    return expanded_numbers

def cleanup_expired_mocks():
    """Remove expired mock entries"""
    current_time = datetime.now()
    expired_keys = []
    
    for key, data in mock_store.items():
        if current_time - data['timestamp'] > timedelta(minutes=MOCK_TIMEOUT_MINUTES):
            expired_keys.append(key)
    
    for key in expired_keys:
        del mock_store[key]
        logger.info(f"Expired mock entry removed: {key}")

async def get_asterisk_channels() -> List[Dict[str, Any]]:
    """Get active channels from Asterisk ARI"""
    try:
        auth = aiohttp.BasicAuth(ASTERISK_ARI_USERNAME, ASTERISK_ARI_PASSWORD)
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.get(f"{ASTERISK_ARI_URL}/channels") as response:
                if response.status == 200:
                    channels = await response.json()
                    logger.info(f"Retrieved {len(channels)} channels from Asterisk")
                    return channels
                else:
                    logger.error(f"Failed to get channels: HTTP {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Error connecting to Asterisk ARI: {e}")
        return []

def match_channel(channel: Dict[str, Any], dialed_number: str, caller_id: Optional[str] = None) -> bool:
    """Check if channel matches the dialed number and caller ID - detects calls in ANY state on Asterisk"""
    try:
        # Get channel information
        channel_id = channel.get('id', 'unknown')
        channel_state = channel.get('state', '')
        connected_line = channel.get('connected', {}).get('number', '')
        caller_id_num = channel.get('caller', {}).get('number', '')
        exten = channel.get('dialplan', {}).get('exten', '')
        channel_name = channel.get('name', '')
        
        # Normalize numbers for comparison
        dialed_last_digits = get_last_digits(dialed_number)
        
        # Check B number (dialed number) in multiple places
        b_number_match = False
        match_source = ""
        
        # 1. Check connected line number
        if connected_line:
            connected_last_digits = get_last_digits(connected_line)
            if dialed_last_digits == connected_last_digits:
                b_number_match = True
                match_source = f"connected_line({connected_line})"
        
        # 2. Check dialplan extension
        if not b_number_match and exten:
            exten_last_digits = get_last_digits(exten)
            if dialed_last_digits == exten_last_digits:
                b_number_match = True
                match_source = f"extension({exten})"
        
        # 3. Check caller ID number (in case it's the dialed number)
        if not b_number_match and caller_id_num:
            caller_last_digits = get_last_digits(caller_id_num)
            if dialed_last_digits == caller_last_digits:
                b_number_match = True
                match_source = f"caller_id({caller_id_num})"
        
        # 4. Check channel name for the number (common in Asterisk)
        if not b_number_match and channel_name:
            # Extract numbers from channel name (e.g., "SIP/19025809678-00000001")
            import re
            numbers_in_name = re.findall(r'\d{7,}', channel_name)
            for num in numbers_in_name:
                if get_last_digits(num) == dialed_last_digits:
                    b_number_match = True
                    match_source = f"channel_name({num})"
                    break
        
        # Check caller ID if provided (for A number verification)
        caller_id_match = True
        if caller_id:
            caller_id_last_digits = get_last_digits(caller_id)
            asterisk_caller_last_digits = get_last_digits(caller_id_num)
            caller_id_match = caller_id_last_digits == asterisk_caller_last_digits
        
        # Accept ANY channel state - if it exists on Asterisk, it's active
        # Remove state filtering to detect calls in all states (early media, connected, playing audio, etc.)
        state_match = True  # Accept all states
        
        match_result = b_number_match and caller_id_match and state_match
        
        # Enhanced logging for debugging
        logger.info(f"Channel {channel_id} matching details:")
        logger.info(f"  - State: '{channel_state}' (accepting all states)")
        logger.info(f"  - Channel name: '{channel_name}'")
        logger.info(f"  - Dialed number match: {b_number_match} via {match_source if b_number_match else 'NO_MATCH'}")
        logger.info(f"  - Looking for last digits: {dialed_last_digits}")
        logger.info(f"  - Connected line: '{connected_line}' -> {get_last_digits(connected_line) if connected_line else 'None'}")
        logger.info(f"  - Extension: '{exten}' -> {get_last_digits(exten) if exten else 'None'}")
        logger.info(f"  - Caller ID: '{caller_id_num}' -> {get_last_digits(caller_id_num) if caller_id_num else 'None'}")
        if caller_id:
            logger.info(f"  - Caller ID match: {caller_id_match} (looking for: {get_last_digits(caller_id)})")
        logger.info(f"  - Overall match: {match_result}")
        
        if match_result:
            logger.info(f"✅ CALL FOUND ON ASTERISK: {channel_id} - State: {channel_state} - Matched via: {match_source}")
        
        return match_result
        
    except Exception as e:
        logger.error(f"Error matching channel: {e}")
        return False

# Authentication dependency
async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key from header"""
    if x_api_key not in [API_KEY, DEV_API_KEY]:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

async def verify_dev_api_key(x_api_key: str = Header(...)):
    """Verify development API key from header"""
    if x_api_key != DEV_API_KEY:
        raise HTTPException(status_code=401, detail="Development API key required")
    return x_api_key

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting Asterisk API Backend")
    yield
    logger.info("Shutting down Asterisk API Backend")

# FastAPI app initialization
app = FastAPI(
    title="Asterisk API Backend",
    description="API for checking call existence on Asterisk server",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Main endpoint: Check connection
@app.get("/check-connection", response_model=ConnectionResponse)
async def check_connection(
    dialed_number: str = Query(..., description="Dialed phone number in E.164 format"),
    caller_id: Optional[str] = Query(None, description="Caller ID number"),
    api_key: str = Depends(verify_api_key)
):
    """
    Check if a dialed call exists on the Asterisk server
    """
    try:
        # Clean up expired mocks first
        cleanup_expired_mocks()
        
        # Normalize the dialed number
        normalized_dialed = normalize_phone_number(dialed_number)
        dialed_last_digits = get_last_digits(normalized_dialed)
        
        # Check if number is in mock store
        if dialed_last_digits in mock_store:
            mock_data = mock_store[dialed_last_digits]
            logger.info(f"Mock connection found for {dialed_last_digits}")
            return ConnectionResponse(
                connected=True,
                channel_id=f"mock-{dialed_last_digits}-{int(time.time())}",
                message="Mock connection active",
                timestamp=datetime.now().isoformat()
            )
        
        # Query Asterisk ARI for active channels
        channels = await get_asterisk_channels()
        
        # DEBUG: Log all channel data for troubleshooting
        logger.info(f"=== DEBUG: All {len(channels)} channels on Asterisk ===")
        for i, channel in enumerate(channels):
            logger.info(f"Channel {i+1}: {channel}")
        logger.info("=== END DEBUG ===")
        
        # Find matching channel
        matching_channel = None
        for channel in channels:
            if match_channel(channel, normalized_dialed, caller_id):
                matching_channel = channel
                break
            else:
                # DEBUG: Log why this channel didn't match
                logger.info(f"❌ Channel {channel.get('id', 'unknown')} did NOT match:")
                logger.info(f"   Raw channel data: {channel}")
                logger.info(f"   Looking for number ending in: {get_last_digits(normalized_dialed)}")
        
        if matching_channel:
            logger.info(f"Call found on Asterisk: {matching_channel.get('id')}")
            return ConnectionResponse(
                connected=True,
                channel_id=matching_channel.get('id'),
                message="Call exists on Asterisk server",
                timestamp=datetime.now().isoformat()
            )
        else:
            logger.info(f"❌ NO MATCHING CALL FOUND for {dialed_last_digits}")
            logger.info(f"   Total channels checked: {len(channels)}")
            return ConnectionResponse(
                connected=False,
                channel_id=None,
                message="Call not found on Asterisk server",
                timestamp=datetime.now().isoformat()
            )
            
    except Exception as e:
        logger.error(f"Error checking connection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Mock connection endpoint for debugging
@app.post("/mock-connect")
async def mock_connect(
    request: MockConnectRequest,
    api_key: str = Depends(verify_dev_api_key)
):
    """
    Add numbers to mock store for debugging (dev-only)
    """
    try:
        expanded_numbers = parse_number_ranges(request.numbers)
        current_time = datetime.now()
        
        added_count = 0
        for number in expanded_numbers:
            last_digits = get_last_digits(number)
            mock_store[last_digits] = {
                'timestamp': current_time,
                'original_number': number
            }
            added_count += 1
        
        logger.info(f"Added {added_count} numbers to mock store")
        
        return {
            "message": f"Added {added_count} numbers to mock store",
            "numbers_added": expanded_numbers,
            "expires_at": (current_time + timedelta(minutes=MOCK_TIMEOUT_MINUTES)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error adding mock connections: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Clear mocks endpoint
@app.delete("/clear-mocks", response_model=MockClearResponse)
async def clear_mocks(api_key: str = Depends(verify_dev_api_key)):
    """
    Clear all mock connections (dev-only)
    """
    try:
        cleared_count = len(mock_store)
        mock_store.clear()
        
        logger.info(f"Cleared {cleared_count} mock entries")
        
        return MockClearResponse(
            cleared_count=cleared_count,
            message=f"Cleared {cleared_count} mock entries"
        )
        
    except Exception as e:
        logger.error(f"Error clearing mocks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Disconnect call endpoint
@app.post("/disconnect-call")
async def disconnect_call(
    request: DisconnectRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Disconnect a call via Asterisk ARI
    """
    try:
        # Handle mock channels
        if request.channel_id.startswith("mock-"):
            # Extract number from mock channel ID and remove from store
            parts = request.channel_id.split("-")
            if len(parts) >= 2:
                number = parts[1]
                if number in mock_store:
                    del mock_store[number]
                    logger.info(f"Removed mock entry: {number}")
            
            return {
                "message": "Mock call disconnected",
                "channel_id": request.channel_id,
                "timestamp": datetime.now().isoformat()
            }
        
        # Disconnect real channel via ARI
        auth = aiohttp.BasicAuth(ASTERISK_ARI_USERNAME, ASTERISK_ARI_PASSWORD)
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.delete(f"{ASTERISK_ARI_URL}/channels/{request.channel_id}") as response:
                if response.status in [204, 404]:  # 204 = success, 404 = already gone
                    logger.info(f"Channel disconnected: {request.channel_id}")
                    return {
                        "message": "Call disconnected successfully",
                        "channel_id": request.channel_id,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.error(f"Failed to disconnect channel: HTTP {response.status}")
                    raise HTTPException(status_code=500, detail="Failed to disconnect call")
                    
    except Exception as e:
        logger.error(f"Error disconnecting call: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Get mock status endpoint
@app.get("/mock-status")
async def get_mock_status(api_key: str = Depends(verify_dev_api_key)):
    """
    Get current mock store status (dev-only)
    """
    try:
        cleanup_expired_mocks()
        
        active_mocks = []
        for number, data in mock_store.items():
            expires_at = data['timestamp'] + timedelta(minutes=MOCK_TIMEOUT_MINUTES)
            active_mocks.append({
                "number": number,
                "original_number": data['original_number'],
                "created_at": data['timestamp'].isoformat(),
                "expires_at": expires_at.isoformat()
            })
        
        return {
            "active_mocks": active_mocks,
            "total_count": len(active_mocks),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting mock status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

