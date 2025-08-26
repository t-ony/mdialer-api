# HTTPS Setup Guide

This guide explains how to enable HTTPS for secure API communication between the mobile app and the Asterisk API backend.

## Why HTTPS?

- **Security**: Encrypts API keys and call data in transit
- **Privacy**: Prevents man-in-the-middle attacks
- **Best Practice**: Industry standard for API communication

## Quick Setup (Development/Testing)

### 1. Generate Self-Signed Certificates

```bash
# Run the certificate generation script
./generate-ssl-cert.sh
```

This creates:
- `certs/key.pem` - Private key
- `certs/cert.pem` - Self-signed certificate

### 2. Start the API Server

```bash
# Build and start with HTTPS support
docker-compose up --build
```

The server will:
- Start HTTPS on port **8443** (if certificates exist)
- Fall back to HTTP on port **8000** (if no certificates)

### 3. Configure Mobile App

In the mobile app settings:
1. Enable **"Use HTTPS"** toggle
2. Set **API Port** to `8443`
3. Accept the self-signed certificate warning

## Production Setup

### 1. Obtain Real SSL Certificates

Replace self-signed certificates with proper ones from a trusted CA:

```bash
# Copy your real certificates
cp your-domain.key certs/key.pem
cp your-domain.crt certs/cert.pem
```

### 2. Update Configuration

Update your `.env` file:

```env
# HTTPS Configuration
HTTPS_PORT=8443
HTTP_PORT=8000
SSL_KEYFILE=/app/certs/key.pem
SSL_CERTFILE=/app/certs/cert.pem
```

### 3. Firewall Configuration

Ensure your firewall allows HTTPS traffic:

```bash
# Allow HTTPS port
sudo ufw allow 8443/tcp
```

## Mobile App Configuration

### Default Settings (Secure)

The mobile app now defaults to:
- **HTTPS**: Enabled
- **Port**: 8000 (you should change to 8443 for HTTPS)

### Settings Location

Go to **Settings** → **Asterisk API Settings**:
- Toggle **"Use HTTPS"** (shows lock icon when enabled)
- Set **API Port** to `8443` for HTTPS
- Set **API Port** to `8000` for HTTP

## Troubleshooting

### Certificate Warnings

**Self-signed certificates** will show security warnings:
- **Android**: Accept the certificate in your app
- **Development**: This is expected behavior

### Connection Issues

1. **Check certificates exist**:
   ```bash
   ls -la certs/
   ```

2. **Check server logs**:
   ```bash
   docker-compose logs mdialer-api
   ```

3. **Test HTTPS endpoint**:
   ```bash
   curl -k https://192.155.107.226:8443/health
   ```

### Port Conflicts

If port 8443 is in use:
1. Change `HTTPS_PORT` in `.env`
2. Update `docker-compose.yml` port mapping
3. Update mobile app port setting

## Security Notes

- **Self-signed certificates**: Only for development/testing
- **Production**: Use certificates from trusted CA (Let's Encrypt, etc.)
- **API Keys**: Still transmitted securely over HTTPS
- **Firewall**: Only expose necessary ports (8443 for HTTPS)

## Migration from HTTP

1. **Generate certificates** (see above)
2. **Enable HTTPS** in mobile app settings
3. **Change port** from 8000 to 8443
4. **Test connection** using the test button
5. **Verify logs** show HTTPS connections

The API backend supports both HTTP and HTTPS simultaneously during migration.

