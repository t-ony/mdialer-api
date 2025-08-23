# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Configure Environment
```bash
cp .env.example .env
nano .env
```

Update these values in `.env`:
```bash
# Your Asterisk server details
ASTERISK_ARI_URL=http://your-asterisk-server:8088/ari
ASTERISK_ARI_USERNAME=your_ari_username
ASTERISK_ARI_PASSWORD=your_ari_password

# Secure API keys (change these!)
API_KEY=your-secure-api-key-here
DEV_API_KEY=your-dev-api-key-here
```

### 2. Start with Docker (Recommended)
```bash
docker-compose up -d
```

### 3. Or Start Locally
```bash
pip install -r requirements.txt
python main.py
```

### 4. Test the API
```bash
# Health check
curl http://localhost:8000/health

# Test with mock data (development)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-dev-api-key-here" \
  -d '{"numbers": ["1234567890"]}' \
  http://localhost:8000/mock-connect

# Check connection
curl -H "X-API-Key: your-api-key-here" \
  "http://localhost:8000/check-connection?dialed_number=1234567890"
```

## 📱 Mobile App Integration

### Call Flow
1. App dials number → Query `/check-connection`
2. If `connected: true` → Continue call
3. If `connected: false` → Hang up locally

### Example Request
```javascript
const response = await fetch(`${API_URL}/check-connection?dialed_number=${number}&caller_id=${callerId}`, {
  headers: {
    'X-API-Key': 'your-api-key'
  }
});

const result = await response.json();
if (result.connected) {
  // Continue call flow
} else {
  // Hang up call
}
```

## 🔧 Development Mode

Use mock mode for testing without Asterisk:

```bash
# Add test numbers
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key" \
  -d '{"numbers": ["555-0100:555-0199"]}' \
  http://localhost:8000/mock-connect

# Test connection (will return connected: true)
curl -H "X-API-Key: api-key" \
  "http://localhost:8000/check-connection?dialed_number=5550150"
```

## 📚 Documentation

- **Full API Docs**: http://localhost:8000/docs (when running)
- **README.md**: Complete documentation
- **DEPLOYMENT.md**: Production deployment guide
- **test_api.py**: Comprehensive test suite

## ⚡ Quick Test

Run the test suite:
```bash
python test_api.py
```

## 🆘 Need Help?

1. Check logs: `docker-compose logs -f mdialer-api`
2. Verify Asterisk ARI: `curl -u username:password http://asterisk:8088/ari/channels`
3. Test health: `curl http://localhost:8000/health`

---

**Ready to integrate with your mobile app!** 🎉

