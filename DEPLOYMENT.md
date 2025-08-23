# Deployment Guide

This guide covers deploying the Mobile Dialer Asterisk API in production environments.

## Production Deployment

### 1. Server Requirements

**Minimum Requirements:**
- 1 CPU core
- 512 MB RAM
- 10 GB disk space
- Ubuntu 20.04+ or similar Linux distribution

**Recommended:**
- 2+ CPU cores
- 2 GB RAM
- 20 GB disk space
- Load balancer for high availability

### 2. Docker Deployment (Recommended)

#### Prerequisites
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### Deployment Steps

1. **Clone and Configure**
```bash
git clone https://github.com/t-ony/mdialer-api.git
cd mdialer-api
cp .env.example .env
```

2. **Edit Production Configuration**
```bash
nano .env
```

Example production `.env`:
```bash
# Asterisk Configuration
ASTERISK_ARI_URL=https://your-asterisk-server.com:8089/ari
ASTERISK_ARI_USERNAME=api_user
ASTERISK_ARI_PASSWORD=secure_password_here

# API Security
API_KEY=your-very-secure-api-key-32-chars-min
DEV_API_KEY=dev-key-for-testing-only

# Mock Configuration
MOCK_TIMEOUT_MINUTES=5
```

3. **Deploy with Docker Compose**
```bash
docker-compose up -d
```

4. **Verify Deployment**
```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs -f mdialer-api

# Test health endpoint
curl http://localhost:8000/health
```

### 3. Reverse Proxy Setup (Nginx)

#### Install Nginx
```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

#### Nginx Configuration
Create `/etc/nginx/sites-available/mdialer-api`:

```nginx
server {
    listen 80;
    server_name your-api-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-api-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-api-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-api-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    
    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint (no rate limiting)
    location /health {
        limit_req off;
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Enable Site and SSL
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/mdialer-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d your-api-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Asterisk Server Configuration

### 1. ARI Configuration

#### `/etc/asterisk/http.conf`
```ini
[general]
enabled=yes
bindaddr=0.0.0.0
bindport=8088

; Enable HTTPS
tlsenable=yes
tlsbindaddr=0.0.0.0:8089
tlscertfile=/etc/asterisk/keys/asterisk.crt
tlsprivatekey=/etc/asterisk/keys/asterisk.key

; Security
sessionlimit=100
session_inactivity=30000
session_keep_alive=15000
```

#### `/etc/asterisk/ari.conf`
```ini
[general]
enabled=yes
pretty=yes
allowed_origins=https://your-api-domain.com

[api_user]
type=user
read_only=no
password=secure_password_here
```

### 2. Security Configuration

#### Firewall Rules
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (redirect)
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow from YOUR_API_SERVER_IP to any port 8089  # ARI HTTPS
sudo ufw enable
```

#### Asterisk Security
```bash
# Create dedicated ARI user with limited permissions
# In /etc/asterisk/manager.conf
[api_user]
secret=secure_password_here
read=system,call,log,verbose,command,agent,user,config,command,dtmf,reporting,cdr,dialplan
write=system,call,log,verbose,command,agent,user,config,command,dtmf,reporting,cdr,dialplan
```

## Monitoring and Logging

### 1. Application Logs

#### Docker Logs
```bash
# View real-time logs
docker-compose logs -f mdialer-api

# Export logs
docker-compose logs mdialer-api > api-logs.txt
```

#### Log Rotation
Create `/etc/logrotate.d/mdialer-api`:
```
/var/lib/docker/containers/*/*-json.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    postrotate
        docker kill -s USR1 $(docker ps -q)
    endscript
}
```

### 2. Health Monitoring

#### Systemd Service for Health Checks
Create `/etc/systemd/system/mdialer-api-health.service`:
```ini
[Unit]
Description=Mobile Dialer API Health Check
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/curl -f http://localhost:8000/health
User=nobody
```

Create `/etc/systemd/system/mdialer-api-health.timer`:
```ini
[Unit]
Description=Run Mobile Dialer API Health Check every 5 minutes
Requires=mdialer-api-health.service

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```

Enable monitoring:
```bash
sudo systemctl enable mdialer-api-health.timer
sudo systemctl start mdialer-api-health.timer
```

### 3. Performance Monitoring

#### Basic Monitoring Script
Create `/usr/local/bin/monitor-api.sh`:
```bash
#!/bin/bash

LOG_FILE="/var/log/mdialer-api-monitor.log"
API_URL="http://localhost:8000/health"

# Check API health
if curl -f -s "$API_URL" > /dev/null; then
    echo "$(date): API healthy" >> "$LOG_FILE"
else
    echo "$(date): API unhealthy - restarting" >> "$LOG_FILE"
    docker-compose -f /path/to/mdialer-api/docker-compose.yml restart mdialer-api
fi

# Check resource usage
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep mdialer-api >> "$LOG_FILE"
```

## Backup and Recovery

### 1. Configuration Backup
```bash
#!/bin/bash
# backup-config.sh

BACKUP_DIR="/backup/mdialer-api"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup configuration
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" \
    /path/to/mdialer-api/.env \
    /path/to/mdialer-api/docker-compose.yml \
    /etc/nginx/sites-available/mdialer-api

# Keep only last 30 days
find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +30 -delete
```

### 2. Disaster Recovery
```bash
# Stop services
docker-compose down

# Restore configuration
tar -xzf /backup/mdialer-api/config_YYYYMMDD_HHMMSS.tar.gz -C /

# Restart services
docker-compose up -d
sudo systemctl reload nginx
```

## Scaling and High Availability

### 1. Load Balancing

#### Multiple API Instances
```yaml
# docker-compose.yml for multiple instances
version: '3.8'

services:
  mdialer-api-1:
    build: .
    ports:
      - "8001:8000"
    environment:
      - INSTANCE_ID=1
    # ... other config

  mdialer-api-2:
    build: .
    ports:
      - "8002:8000"
    environment:
      - INSTANCE_ID=2
    # ... other config
```

#### Nginx Load Balancer
```nginx
upstream mdialer_api {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    # ... SSL config
    
    location / {
        proxy_pass http://mdialer_api;
        # ... proxy config
    }
}
```

### 2. Database for Shared State

For production with multiple instances, consider using Redis for shared mock state:

```python
# Add to requirements.txt
redis==4.5.1

# Update main.py to use Redis instead of in-memory dict
import redis

redis_client = redis.Redis(host='redis', port=6379, db=0)
```

## Troubleshooting

### Common Issues

1. **API Not Responding**
   ```bash
   # Check container status
   docker-compose ps
   
   # Check logs
   docker-compose logs mdialer-api
   
   # Restart service
   docker-compose restart mdialer-api
   ```

2. **Asterisk Connection Failed**
   ```bash
   # Test ARI connectivity
   curl -u username:password http://asterisk-server:8088/ari/channels
   
   # Check Asterisk logs
   asterisk -rx "core show channels"
   ```

3. **High Memory Usage**
   ```bash
   # Monitor container resources
   docker stats
   
   # Restart if needed
   docker-compose restart mdialer-api
   ```

### Performance Tuning

1. **Uvicorn Workers**
   ```yaml
   # In docker-compose.yml
   command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
   ```

2. **Connection Pooling**
   ```python
   # Add to main.py for better performance
   import aiohttp
   
   # Create session pool
   connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
   session = aiohttp.ClientSession(connector=connector)
   ```

## Security Checklist

- [ ] Strong API keys (32+ characters)
- [ ] HTTPS enabled with valid certificates
- [ ] Firewall configured
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] Asterisk ARI secured with strong credentials
- [ ] Regular security updates
- [ ] Log monitoring enabled
- [ ] Backup strategy implemented

