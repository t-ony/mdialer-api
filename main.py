"""
Asterisk API Backend for Mobile Dialer App
Provides endpoints to check call existence on Asterisk server via AMI
"""

import os
import re
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

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
ASTERISK_AMI_HOST = os.getenv("ASTERISK_AMI_HOST", "host.docker.internal")
ASTERISK_AMI_PORT = int(os.getenv("ASTERISK_AMI_PORT", "5038"))
ASTERISK_AMI_USERNAME = os.getenv("ASTERISK_AMI_USERNAME", "admin")
ASTERISK_AMI_PASSWORD = os.getenv("ASTERISK_AMI_PASSWORD", "amp111")
API_KEY = os.getenv("API_KEY", "your-secure-api-key")
DEV_API_KEY = os.getenv("DEV_API_KEY", "dev-api-key")
MOCK_TIMEOUT_MINUTES = int(os.getenv("MOCK_TIMEOUT_MINUTES", "5"))

# In-memory storage for mock connections
mock_store: Dict[str, Dict[str, Any]] = {}

# Pydantic models
class MockConnectRequest(BaseModel):
    numbers: List[str] = Field(..., description="List of phone numbers")

class ConnectionResponse(BaseModel):
    connected: bool
    channel_id: Optional[str] = None
    message: str
    timestamp: str

class DisconnectRequest(BaseModel):
    channel_id: str = Field(..., description="Channel ID to disconnect")

# FastAPI app
app = FastAPI(
    title="Asterisk Mobile Dialer API",
    description="API for checking call existence on Asterisk server via AMI",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility functions
def normalize_phone_number(number: str) -> str:
    """Normalize phone number to E.164 format"""
    return re.sub(r'[^\d]', '', number)

def get_last_digits(number: str, digits: int = 7) -> str:
    """Get last N digits of a phone number"""
    normalized = normalize_phone_number(number)
    return normalized[-digits:] if len(normalized) >= digits else normalized

def cleanup_expired_mocks():
    """Remove expired mock entries"""
    current_time = time.time()
    expired_keys = []
    
    for key, data in mock_store.items():
        if current_time - data['timestamp'] > (MOCK_TIMEOUT_MINUTES * 60):
            expired_keys.append(key)
    
    for key in expired_keys:
        del mock_store[key]
        logger.info(f"Expired mock entry removed: {key}")

# AMI Connection Class
class AMIConnection:
    def __init__(self):
        self.reader = None
        self.writer = None
        
    async def connect(self):
        """Connect to Asterisk AMI"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                ASTERISK_AMI_HOST, ASTERISK_AMI_PORT
            )
            
            # Read initial AMI banner
            banner = await self.reader.read(1024)
            logger.info(f"AMI Banner: {banner.decode().strip()}")
            
            # Login to AMI
            login_msg = (
                f"Action: Login\r\n"
                f"Username: {ASTERISK_AMI_USERNAME}\r\n"
                f"Secret: {ASTERISK_AMI_PASSWORD}\r\n"
                f"Events: off\r\n\r\n"
            )
            self.writer.write(login_msg.encode())
            await self.writer.drain()
            
            # Read login response with timeout
            login_response = b""
            timeout_count = 0
            max_timeout = 10  # 10 iterations max
            
            while timeout_count < max_timeout:
                try:
                    # Use wait_for with timeout to avoid hanging
                    chunk = await asyncio.wait_for(self.reader.read(1024), timeout=1.0)
                    if not chunk:
                        break
                    login_response += chunk
                    
                    # Check if we have complete response (ends with double CRLF)
                    if b"\r\n\r\n" in login_response:
                        break
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    # If we have some data and it contains a response, break
                    if login_response and (b"Response:" in login_response):
                        break
            
            response_text = login_response.decode().strip()
            logger.info(f"AMI Login Response: {response_text}")
            
            # Check for successful login
            if "Response: Success" in response_text and "Authentication accepted" in response_text:
                logger.info("Successfully connected to Asterisk AMI")
                return True
            elif "Response: Success" in response_text:
                logger.info("Successfully connected to Asterisk AMI (basic success)")
                return True
            else:
                logger.error(f"AMI login failed. Response: {response_text}")
                await self.disconnect()
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to Asterisk AMI: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from AMI"""
        try:
            if self.writer:
                logout_msg = "Action: Logoff\r\n\r\n"
                self.writer.write(logout_msg.encode())
                await self.writer.drain()
                self.writer.close()
                await self.writer.wait_closed()
        except Exception as e:
            logger.error(f"Error disconnecting from AMI: {e}")
    
    async def get_channels(self) -> List[Dict[str, Any]]:
        """Get all active channels from Asterisk"""
        try:
            # Send CoreShowChannels command
            channels_msg = (
                f"Action: CoreShowChannels\r\n"
                f"ActionID: channels{int(time.time())}\r\n\r\n"
            )
            self.writer.write(channels_msg.encode())
            await self.writer.drain()
            
            # Read response
            channels_data = b""
            while True:
                chunk = await self.reader.read(4096)
                if not chunk:
                    break
                channels_data += chunk
                # Check if we have complete response
                if b"Event: CoreShowChannelsComplete" in channels_data:
                    break
            
            # Parse channel data
            channels = self._parse_channels(channels_data.decode())
            logger.info(f"Retrieved {len(channels)} channels from Asterisk AMI")
            return channels
            
        except Exception as e:
            logger.error(f"Error getting channels from AMI: {e}")
            return []
    
    def _parse_channels(self, ami_data: str) -> List[Dict[str, Any]]:
        """Parse AMI CoreShowChannels response"""
        channels = []
        
        # Split by events
        events = ami_data.split("Event: CoreShowChannel")
        
        for event in events[1:]:  # Skip first empty split
            channel = {}
            lines = event.strip().split('\r\n')
            
            for line in lines:
                if ':' in line and not line.startswith('Event:'):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Store all fields
                    channel[key.lower()] = value
            
            if channel and 'channel' in channel:  # Only add valid channels
                channels.append(channel)
        
        return channels
    
    async def hangup_channel(self, channel_id: str) -> bool:
        """Hangup a specific channel"""
        try:
            hangup_msg = (
                f"Action: Hangup\r\n"
                f"Channel: {channel_id}\r\n"
                f"ActionID: hangup{int(time.time())}\r\n\r\n"
            )
            self.writer.write(hangup_msg.encode())
            await self.writer.drain()
            
            # Read response
            response = await self.reader.read(1024)
            return b"Success" in response
            
        except Exception as e:
            logger.error(f"Error hanging up channel {channel_id}: {e}")
            return False

# Channel matching function
def match_channel(channel: Dict[str, Any], dialed_number: str) -> bool:
    """Check if channel matches the dialed number"""
    try:
        dialed_last_digits = get_last_digits(dialed_number)
        
        # Convert entire channel to string and search for the number
        channel_str = str(channel)
        
        # Extract ALL numbers from the channel data
        all_numbers = re.findall(r'\d{7,}', channel_str)
        
        # Check if our target number (last 7 digits) appears anywhere
        for num in all_numbers:
            if get_last_digits(num) == dialed_last_digits:
                logger.info(f"✅ CALL FOUND: {channel.get('channel', 'unknown')} - Number {dialed_last_digits} found as {num}")
                logger.info(f"   Channel state: {channel.get('channelstatedesc', 'unknown')}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error matching channel: {e}")
        return False

# Authentication
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

async def verify_dev_api_key(x_api_key: str = Header(...)):
    if x_api_key != DEV_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid dev API key")
    return x_api_key

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/check-connection", response_model=ConnectionResponse)
async def check_connection(
    dialed_number: str = Query(..., description="Dialed phone number in E.164 format"),
    caller_id: Optional[str] = Query(None, description="Caller ID number"),
    api_key: str = Depends(verify_api_key)
):
    """Check if a dialed call exists on the Asterisk server"""
    try:
        # Clean up expired mocks first
        cleanup_expired_mocks()
        
        # Normalize the dialed number
        normalized_dialed = normalize_phone_number(dialed_number)
        dialed_last_digits = get_last_digits(normalized_dialed)
        
        # Check if number is in mock store
        if dialed_last_digits in mock_store:
            logger.info(f"Mock connection found for {dialed_last_digits}")
            return ConnectionResponse(
                connected=True,
                channel_id=f"mock-{dialed_last_digits}-{int(time.time())}",
                message="Mock connection active",
                timestamp=datetime.now().isoformat()
            )
        
        # Connect to AMI and get channels
        ami = AMIConnection()
        if not await ami.connect():
            raise HTTPException(status_code=500, detail="Failed to connect to Asterisk AMI")
        
        try:
            channels = await ami.get_channels()
            
            # Find matching channel
            matching_channel = None
            for channel in channels:
                if match_channel(channel, normalized_dialed):
                    matching_channel = channel
                    break
            
            if matching_channel:
                logger.info(f"Call found on Asterisk: {matching_channel.get('channel')}")
                return ConnectionResponse(
                    connected=True,
                    channel_id=matching_channel.get('channel'),
                    message="Call exists on Asterisk server",
                    timestamp=datetime.now().isoformat()
                )
            else:
                logger.info(f"No matching call found for {dialed_last_digits}")
                return ConnectionResponse(
                    connected=False,
                    channel_id=None,
                    message="Call not found on Asterisk server",
                    timestamp=datetime.now().isoformat()
                )
                
        finally:
            await ami.disconnect()
            
    except Exception as e:
        logger.error(f"Error checking connection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/mock-connect")
async def mock_connect(
    request: MockConnectRequest,
    api_key: str = Depends(verify_dev_api_key)
):
    """Add numbers to mock store for debugging"""
    try:
        current_time = time.time()
        added_numbers = []
        
        for number in request.numbers:
            normalized = normalize_phone_number(number)
            last_digits = get_last_digits(normalized)
            
            mock_store[last_digits] = {
                'number': normalized,
                'timestamp': current_time
            }
            added_numbers.append(last_digits)
            logger.info(f"Mock connection added: {last_digits}")
        
        return {
            "message": f"Mock connections added for {len(added_numbers)} numbers",
            "numbers": added_numbers,
            "expires_in_minutes": MOCK_TIMEOUT_MINUTES
        }
        
    except Exception as e:
        logger.error(f"Error adding mock connections: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/clear-mocks")
async def clear_mocks(api_key: str = Depends(verify_dev_api_key)):
    """Clear all mock connections"""
    try:
        count = len(mock_store)
        mock_store.clear()
        logger.info(f"Cleared {count} mock connections")
        return {"message": f"Cleared {count} mock connections"}
        
    except Exception as e:
        logger.error(f"Error clearing mocks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/disconnect-call")
async def disconnect_call(
    request: DisconnectRequest,
    api_key: str = Depends(verify_api_key)
):
    """Disconnect a call via Asterisk AMI"""
    try:
        # For mock channels, just remove from store
        if request.channel_id.startswith("mock-"):
            logger.info(f"Disconnecting mock channel: {request.channel_id}")
            return {"message": "Mock call disconnected", "success": True}
        
        # Disconnect real channel via AMI
        ami = AMIConnection()
        if not await ami.connect():
            raise HTTPException(status_code=500, detail="Failed to connect to Asterisk AMI")
        
        try:
            success = await ami.hangup_channel(request.channel_id)
            
            if success:
                logger.info(f"Successfully disconnected channel: {request.channel_id}")
                return {"message": "Call disconnected successfully", "success": True}
            else:
                logger.error(f"Failed to disconnect channel: {request.channel_id}")
                return {"message": "Failed to disconnect call", "success": False}
                
        finally:
            await ami.disconnect()
            
    except Exception as e:
        logger.error(f"Error disconnecting call: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/mock-status")
async def get_mock_status(api_key: str = Depends(verify_dev_api_key)):
    """Get current mock connections status"""
    cleanup_expired_mocks()
    return {
        "active_mocks": len(mock_store),
        "mock_numbers": list(mock_store.keys()),
        "timeout_minutes": MOCK_TIMEOUT_MINUTES
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Asterisk AMI API Backend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

