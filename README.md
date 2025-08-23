# Mobile Dialer Asterisk API

A FastAPI backend service that integrates with Asterisk's ARI (Asterisk REST Interface) to check call existence and manage call flow for mobile dialer applications.

## Features

- **Call Existence Check**: Verify if dialed calls exist on Asterisk server during early media phase
- **Mock Mode**: Debug functionality with simulated connections for testing
- **Call Disconnection**: Terminate calls via Asterisk ARI
- **Security**: API key authentication for all endpoints
- **Logging**: Comprehensive logging for debugging and auditing
- **Docker Support**: Containerized deployment with docker-compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Asterisk server with ARI enabled
- Python 3.11+ (for local development)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/t-ony/mdialer-api.git
cd mdialer-api
```

2. Copy environment configuration:
```bash
cp .env.example .env
```

3. Edit `.env` file with your Asterisk configuration:
```bash
ASTERISK_ARI_URL=http://your-asterisk-server:8088/ari
ASTERISK_ARI_USERNAME=your_ari_username
ASTERISK_ARI_PASSWORD=your_ari_password
API_KEY=your-secure-api-key
DEV_API_KEY=your-dev-api-key
```

4. Start the service:
```bash
docker-compose up -d
```

The API will be available at `http://localhost:8000`

## API Documentation

### Authentication

All endpoints require an API key passed in the `X-API-Key` header:
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/health
```

### Endpoints

#### Health Check
```http
GET /health
```
Returns service health status.

#### Check Connection
```http
GET /check-connection?dialed_number=1234567890&caller_id=0987654321
```

**Parameters:**
- `dialed_number` (required): Phone number dialed by the app
- `caller_id` (optional): Caller ID of the device

**Response:**
```json
{
  "connected": true,
  "channel_id": "1234567890.123",
  "message": "Call exists on Asterisk server",
  "timestamp": "2024-01-01T12:00:00"
}
```

#### Mock Connect (Development Only)
```http
POST /mock-connect
Content-Type: application/json
X-API-Key: dev-api-key

{
  "numbers": ["1234567890", "555-0100:555-0199"]
}
```

Adds numbers to mock store for testing. Supports individual numbers and ranges.

#### Disconnect Call
```http
POST /disconnect-call
Content-Type: application/json

{
  "channel_id": "1234567890.123"
}
```

Disconnects a call via Asterisk ARI.

#### Clear Mocks (Development Only)
```http
DELETE /clear-mocks
X-API-Key: dev-api-key
```

Clears all mock connections.

#### Mock Status (Development Only)
```http
GET /mock-status
X-API-Key: dev-api-key
```

Returns current mock store status.

## Asterisk Configuration

### Enable ARI in Asterisk

1. Edit `/etc/asterisk/http.conf`:
```ini
[general]
enabled=yes
bindaddr=0.0.0.0
bindport=8088
tlsenable=yes
tlsbindaddr=0.0.0.0:8089
tlscertfile=/path/to/cert.pem
tlsprivatekey=/path/to/private.key
```

2. Edit `/etc/asterisk/ari.conf`:
```ini
[general]
enabled=yes
pretty=yes
allowed_origins=*

[ari_user]
type=user
read_only=no
password=ari_password
```

3. Reload Asterisk modules:
```bash
asterisk -rx "module reload res_http_websocket"
asterisk -rx "module reload res_ari"
```

## Call Matching Logic

The API matches calls using the following criteria:

1. **Number Matching**: Compares last 7 digits of dialed number with Asterisk channel data
2. **Caller ID Matching**: If provided, compares last 7 digits of caller ID
3. **Channel State**: Verifies channel is in valid state (Up, Ringing, Early Media)
4. **Multiple Matches**: Selects most recent/active channel if multiple matches found

## Development

### Local Development

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run development server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

Test the API endpoints using curl or any HTTP client:

```bash
# Health check
curl http://localhost:8000/health

# Check connection (replace with your API key)
curl -H "X-API-Key: your-api-key" \
     "http://localhost:8000/check-connection?dialed_number=1234567890"

# Add mock numbers for testing
curl -X POST \
     -H "Content-Type: application/json" \
     -H "X-API-Key: dev-api-key" \
     -d '{"numbers": ["1234567890", "555-0100:555-0110"]}' \
     http://localhost:8000/mock-connect
```

## Mobile App Integration

### Call Flow

1. **Dial Number**: App dials number using default Android dialer
2. **Check Connection**: Query `/check-connection` endpoint with retry logic
3. **Decision Point**:
   - If `connected: true`: Continue normal call flow (mute, timer, etc.)
   - If `connected: false` after retries: Hang up locally
4. **Disconnect**: Use `/disconnect-call` when ending call

### Retry Logic

Implement retry mechanism in mobile app:
- 3 attempts with 1-2 second delays
- Account for call propagation time to Asterisk
- Log failures for debugging

### Error Handling

Handle API errors gracefully:
- Network errors: Retry with exponential backoff
- 401 Unauthorized: Check API key configuration
- 500 Server Error: Log and retry, fallback to local hangup

## Security Considerations

- Use strong API keys in production
- Enable HTTPS/TLS for all communications
- Restrict CORS origins in production
- Use secure Asterisk ARI credentials
- Monitor API access logs
- Implement rate limiting if needed

## Logging

The application logs all important events:
- API requests and responses
- Asterisk ARI interactions
- Call matching results
- Error conditions
- Mock operations

Logs are written to stdout and can be collected by Docker logging drivers.

## Troubleshooting

### Common Issues

1. **Connection Refused to Asterisk**:
   - Verify Asterisk ARI is enabled and running
   - Check firewall settings
   - Validate ARI credentials

2. **No Matching Calls Found**:
   - Check number normalization logic
   - Verify channel state requirements
   - Review Asterisk dialplan configuration

3. **Authentication Errors**:
   - Verify API key configuration
   - Check header format: `X-API-Key: your-key`

### Debug Mode

Use mock mode for testing without Asterisk:
```bash
# Add test numbers to mock store
curl -X POST \
     -H "Content-Type: application/json" \
     -H "X-API-Key: dev-api-key" \
     -d '{"numbers": ["1234567890"]}' \
     http://localhost:8000/mock-connect

# Test connection check
curl -H "X-API-Key: your-api-key" \
     "http://localhost:8000/check-connection?dialed_number=1234567890"
```

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please create an issue in the GitHub repository.

