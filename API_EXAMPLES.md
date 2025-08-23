# Mobile Dialer Asterisk API - Curl Examples

This document contains ready-to-run curl commands for all API endpoints using your specific configuration.

## Configuration
- **API Key**: `ef19241d-40c1-4711-adc6-682130932d4d`
- **Dev API Key**: `711ddbd9-292a-4212-9850-40fa17ce7405`
- **Test Phone Number**: `19025809678` (E.164 format from mobile dialer)
- **Base URL**: `http://localhost:8000` (update with your server URL)

---

## 1. Health Check

### Basic Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

---

## 2. Check Connection Endpoint

### Check Connection - Basic (No Mock)
```bash
curl -X GET \
  -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  "http://localhost:8000/check-connection?dialed_number=19025809678"
```

### Check Connection - With Caller ID
```bash
curl -X GET \
  -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  "http://localhost:8000/check-connection?dialed_number=19025809678&caller_id=15551234567"
```

### Check Connection - Different Number Format (will normalize to last 7 digits)
```bash
curl -X GET \
  -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  "http://localhost:8000/check-connection?dialed_number=+1-902-580-9678&caller_id=+1-555-123-4567"
```

**Expected Response (when no call exists):**
```json
{
  "connected": false,
  "channel_id": null,
  "message": "Call not found on Asterisk server",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

**Expected Response (when call exists):**
```json
{
  "connected": true,
  "channel_id": "SIP/trunk-00000001",
  "message": "Call exists on Asterisk server",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

---

## 3. Mock Operations (Development/Testing)

### Add Single Mock Number
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" \
  -d '{"numbers": ["19025809678"]}' \
  "http://localhost:8000/mock-connect"
```

### Add Multiple Mock Numbers
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" \
  -d '{"numbers": ["19025809678", "15551234567", "18005551212"]}' \
  "http://localhost:8000/mock-connect"
```

### Add Mock Number Range
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" \
  -d '{"numbers": ["19025809678", "555-0100:555-0110"]}' \
  "http://localhost:8000/mock-connect"
```

### Add Large Mock Range (for testing)
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" \
  -d '{"numbers": ["19025800000:19025809999"]}' \
  "http://localhost:8000/mock-connect"
```

**Expected Response:**
```json
{
  "message": "Added 10000 numbers to mock store",
  "numbers_added": ["19025800000", "19025800001", "..."],
  "expires_at": "2024-01-01T12:05:00.000000"
}
```

---

## 4. Check Connection with Mock Data

### Test Mock Connection (after adding mock)
```bash
# First add mock
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" \
  -d '{"numbers": ["19025809678"]}' \
  "http://localhost:8000/mock-connect"

# Then check connection (should return connected: true)
curl -X GET \
  -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  "http://localhost:8000/check-connection?dialed_number=19025809678"
```

**Expected Response (with mock):**
```json
{
  "connected": true,
  "channel_id": "mock-5809678-1234567890",
  "message": "Mock connection active",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

---

## 5. Mock Status and Management

### Get Mock Status
```bash
curl -X GET \
  -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" \
  "http://localhost:8000/mock-status"
```

**Expected Response:**
```json
{
  "active_mocks": [
    {
      "number": "5809678",
      "original_number": "19025809678",
      "created_at": "2024-01-01T12:00:00.000000",
      "expires_at": "2024-01-01T12:05:00.000000"
    }
  ],
  "total_count": 1,
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

### Clear All Mocks
```bash
curl -X DELETE \
  -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" \
  "http://localhost:8000/clear-mocks"
```

**Expected Response:**
```json
{
  "cleared_count": 1,
  "message": "Cleared 1 mock entries"
}
```

---

## 6. Disconnect Call

### Disconnect Real Call
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  -d '{"channel_id": "SIP/trunk-00000001"}' \
  "http://localhost:8000/disconnect-call"
```

### Disconnect Mock Call
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  -d '{"channel_id": "mock-5809678-1234567890"}' \
  "http://localhost:8000/disconnect-call"
```

**Expected Response:**
```json
{
  "message": "Call disconnected successfully",
  "channel_id": "SIP/trunk-00000001",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

---

## 7. Error Testing

### Invalid API Key
```bash
curl -X GET \
  -H "X-API-Key: invalid-key" \
  "http://localhost:8000/check-connection?dialed_number=19025809678"
```

**Expected Response:**
```json
{
  "detail": "Invalid API key"
}
```

### Missing API Key
```bash
curl -X GET \
  "http://localhost:8000/check-connection?dialed_number=19025809678"
```

**Expected Response:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["header", "x-api-key"],
      "msg": "Field required"
    }
  ]
}
```

### Dev Endpoint with Regular API Key (should fail)
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  -d '{"numbers": ["19025809678"]}' \
  "http://localhost:8000/mock-connect"
```

**Expected Response:**
```json
{
  "detail": "Development API key required"
}
```

---

## 8. Complete Test Workflow

### Full Test Sequence
```bash
#!/bin/bash

echo "=== Mobile Dialer API Test Sequence ==="

# 1. Health Check
echo "1. Testing Health Check..."
curl -s "http://localhost:8000/health" | jq

# 2. Check connection (should be false initially)
echo -e "\n2. Testing Connection Check (no mock)..."
curl -s -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  "http://localhost:8000/check-connection?dialed_number=19025809678" | jq

# 3. Add mock number
echo -e "\n3. Adding Mock Number..."
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" \
  -d '{"numbers": ["19025809678"]}' \
  "http://localhost:8000/mock-connect" | jq

# 4. Check connection again (should be true now)
echo -e "\n4. Testing Connection Check (with mock)..."
RESPONSE=$(curl -s -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  "http://localhost:8000/check-connection?dialed_number=19025809678")
echo $RESPONSE | jq
CHANNEL_ID=$(echo $RESPONSE | jq -r '.channel_id')

# 5. Check mock status
echo -e "\n5. Checking Mock Status..."
curl -s -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" \
  "http://localhost:8000/mock-status" | jq

# 6. Disconnect the mock call
echo -e "\n6. Disconnecting Mock Call..."
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  -d "{\"channel_id\": \"$CHANNEL_ID\"}" \
  "http://localhost:8000/disconnect-call" | jq

# 7. Clear all mocks
echo -e "\n7. Clearing All Mocks..."
curl -s -X DELETE \
  -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" \
  "http://localhost:8000/clear-mocks" | jq

echo -e "\n=== Test Sequence Complete ==="
```

---

## 9. Production Testing

### Test with Your Asterisk Server
```bash
# Update the base URL to your production server
BASE_URL="https://your-api-domain.com"

# Test real Asterisk integration
curl -X GET \
  -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  "$BASE_URL/check-connection?dialed_number=19025809678&caller_id=15551234567"
```

### Load Testing (Multiple Requests)
```bash
# Test multiple concurrent requests
for i in {1..10}; do
  curl -X GET \
    -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
    "http://localhost:8000/check-connection?dialed_number=1902580967$i" &
done
wait
```

---

## 10. Mobile App Integration Examples

### Typical Mobile App Flow
```bash
# 1. App dials number 19025809678
# 2. App immediately queries API (with retry logic)

# First attempt
curl -X GET \
  -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  "http://localhost:8000/check-connection?dialed_number=19025809678&caller_id=15551234567"

# If connected: false, wait 1 second and retry
sleep 1

# Second attempt
curl -X GET \
  -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  "http://localhost:8000/check-connection?dialed_number=19025809678&caller_id=15551234567"

# If still false after 3 attempts, hang up locally
# If true, continue call and eventually disconnect via API
```

---

## Notes

- **Number Normalization**: The API compares the last 7 digits, so `19025809678` matches `5809678`
- **Mock Expiration**: Mock entries expire after 5 minutes by default
- **Rate Limiting**: Consider implementing rate limiting in production
- **HTTPS**: Use HTTPS in production for security
- **Error Handling**: Always check HTTP status codes and handle errors gracefully

## Quick Reference

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/health` | GET | None | Health check |
| `/check-connection` | GET | API Key | Check if call exists |
| `/mock-connect` | POST | Dev Key | Add mock numbers |
| `/mock-status` | GET | Dev Key | View mock status |
| `/clear-mocks` | DELETE | Dev Key | Clear all mocks |
| `/disconnect-call` | POST | API Key | Disconnect call |

