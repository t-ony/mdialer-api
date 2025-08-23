# Quick Curl Commands - Mobile Dialer API

**Your Configuration:**
- API Key: `ef19241d-40c1-4711-adc6-682130932d4d`
- Dev API Key: `711ddbd9-292a-4212-9850-40fa17ce7405`
- Test Number: `19025809678`

## Essential Commands (Copy & Paste Ready)

### 1. Health Check
```bash
curl "http://localhost:8000/health"
```

### 2. Check Connection (Real)
```bash
curl -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  "http://localhost:8000/check-connection?dialed_number=19025809678&caller_id=15551234567"
```

### 3. Add Mock Number
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" \
  -d '{"numbers": ["19025809678"]}' \
  "http://localhost:8000/mock-connect"
```

### 4. Check Connection (Mock)
```bash
curl -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  "http://localhost:8000/check-connection?dialed_number=19025809678"
```

### 5. Mock Status
```bash
curl -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" \
  "http://localhost:8000/mock-status"
```

### 6. Clear Mocks
```bash
curl -X DELETE \
  -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" \
  "http://localhost:8000/clear-mocks"
```

### 7. Disconnect Call
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" \
  -d '{"channel_id": "CHANNEL_ID_HERE"}' \
  "http://localhost:8000/disconnect-call"
```

## Quick Test Sequence
```bash
# 1. Add mock
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" -d '{"numbers": ["19025809678"]}' "http://localhost:8000/mock-connect"

# 2. Check connection (should return connected: true)
curl -H "X-API-Key: ef19241d-40c1-4711-adc6-682130932d4d" "http://localhost:8000/check-connection?dialed_number=19025809678"

# 3. Clear mocks
curl -X DELETE -H "X-API-Key: 711ddbd9-292a-4212-9850-40fa17ce7405" "http://localhost:8000/clear-mocks"
```

## Production URLs
Replace `http://localhost:8000` with your production URL:
- `https://your-domain.com`
- `https://api.your-domain.com`

