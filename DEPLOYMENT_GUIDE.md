# Deployment Guide - Social Media Agent on GCP

Complete guide for deploying the Social Media Agent as a production service on Google Cloud Platform.

## Prerequisites

- GCP account with active project
- GCP VM instance running Debian 11 (or Ubuntu 20.04+)
- SSH access to the VM
- Required API keys:
  - Notion API Key
  - OpenRouter API Key
  - Mastodon Access Token
  - Replicate API Token
  - Telegram Bot Token (for HITL approval)

## Deployment Steps

### Step 1: Access Your VM

```bash
# SSH into your VM
gcloud compute ssh YOUR_VM_NAME --zone=YOUR_ZONE --project=YOUR_PROJECT_ID
```

### Step 2: Transfer Code to VM

**Option A: Clone from Git Repository**
```bash
cd ~
git clone YOUR_REPOSITORY_URL Social-Media-Agent
cd Social-Media-Agent
```

**Option B: Copy from Local Machine**
```bash
# From your local machine
gcloud compute scp --recurse ./Social-Media-Agent YOUR_VM_NAME:~ --zone=YOUR_ZONE
```

### Step 3: Run Setup Script

```bash
cd ~/Social-Media-Agent
chmod +x deploy/setup.sh
./deploy/setup.sh
```

The setup script will:
- Install system dependencies (Python, git, build tools)
- Install `uv` package manager
- Install Python dependencies
- Create `.env` file from template
- Initialize SQLite database
- Create systemd service
- Configure firewall rules

### Step 4: Configure Environment Variables

Edit the `.env` file with your actual API keys:

```bash
nano .env
```

Update these values:
```env
# Notion Configuration
NOTION_API_KEY=secret_your_actual_notion_key_here
NOTION_PAGE_ID=your_actual_page_id_here

# OpenRouter Configuration
OPENROUTER_API_KEY=sk-or-v1-your_actual_openrouter_key_here

# Mastodon Configuration
MASTODON_INSTANCE_URL=https://your-instance.social
MASTODON_ACCESS_TOKEN=your_actual_mastodon_token_here
MASTODON_KEYWORDS=AI,automation,technology
AI_LABEL=#AIGenerated

# Replicate Configuration
REPLICATE_API_TOKEN=your_actual_replicate_token_here
FLUX_MODEL_ID=sundai-club/presence:VERSION_ID
FLUX_TRIGGER_WORD=TANGO

# Telegram Configuration (for HITL approval)
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
TELEGRAM_CHAT_ID=your_actual_chat_id_here

# Database Configuration (optional, defaults to SQLite)
DATABASE_URL=sqlite:///./social_media_agent.db
```

Save and exit (Ctrl+X, then Y, then Enter).

### Step 5: Initialize Database

```bash
source .venv/bin/activate
python3 -c "from src.database import init_db; init_db()"
```

### Step 6: Start the Service

```bash
# Start the service
sudo systemctl start social-media-agent

# Enable auto-start on boot
sudo systemctl enable social-media-agent

# Check service status
sudo systemctl status social-media-agent
```

### Step 7: Verify Deployment

```bash
# Check if the API is responding
curl http://localhost:8000/health

# View service logs
sudo journalctl -u social-media-agent -f
```

Expected output from health check:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-22T20:00:00",
  "database": "healthy",
  "scheduler": "running"
}
```

### Step 8: Test API Endpoints

```bash
# Get your VM's external IP
curl ifconfig.me

# Test from your local machine
curl http://YOUR_VM_IP:8000/

# View interactive API documentation
# Open in browser: http://YOUR_VM_IP:8000/docs
```

---

## Firewall Configuration

### GCP Firewall Rules

Allow incoming traffic on port 8000:

```bash
# Via gcloud command
gcloud compute firewall-rules create allow-social-media-api \
  --project=YOUR_PROJECT_ID \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=tcp:8000 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=http-server

# Or via GCP Console:
# 1. Go to VPC Network > Firewall
# 2. Create Firewall Rule
# 3. Name: allow-social-media-api
# 4. Direction: Ingress
# 5. Action: Allow
# 6. Targets: Specified target tags (http-server)
# 7. Source filter: IPv4 ranges (0.0.0.0/0)
# 8. Protocols and ports: tcp:8000
```

### VM Firewall (UFW)

```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow API port
sudo ufw allow 8000/tcp

# Check status
sudo ufw status
```

---

## Optional: Nginx Reverse Proxy

For production, use Nginx as a reverse proxy:

### Install Nginx

```bash
sudo apt-get install nginx
```

### Configure Nginx

```bash
# Copy config file
sudo cp ~/Social-Media-Agent/deploy/nginx.conf /etc/nginx/sites-available/social-media-agent

# Update VM IP in config
sudo nano /etc/nginx/sites-available/social-media-agent

# Enable site
sudo ln -s /etc/nginx/sites-available/social-media-agent /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Update Firewall for HTTP

```bash
# Allow HTTP traffic
sudo ufw allow 80/tcp

# GCP firewall (if not already allowed)
gcloud compute firewall-rules create allow-http \
  --project=YOUR_PROJECT_ID \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=tcp:80 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=http-server
```

---

## Service Management

### Common Commands

```bash
# Start service
sudo systemctl start social-media-agent

# Stop service
sudo systemctl stop social-media-agent

# Restart service
sudo systemctl restart social-media-agent

# Check status
sudo systemctl status social-media-agent

# View logs (real-time)
sudo journalctl -u social-media-agent -f

# View last 100 lines of logs
sudo journalctl -u social-media-agent -n 100

# Enable auto-start on boot
sudo systemctl enable social-media-agent

# Disable auto-start
sudo systemctl disable social-media-agent
```

### Updating the Service

```bash
# Stop service
sudo systemctl stop social-media-agent

# Pull latest changes
cd ~/Social-Media-Agent
git pull

# Update dependencies
uv sync

# Restart service
sudo systemctl start social-media-agent
```

---

## Monitoring and Maintenance

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health | jq

# Check database
sqlite3 social_media_agent.db "SELECT COUNT(*) FROM posts;"

# Check scheduler jobs
curl http://localhost:8000/api/schedules
```

### Log Analysis

```bash
# Check for errors
sudo journalctl -u social-media-agent | grep ERROR

# Check recent activity
sudo journalctl -u social-media-agent --since "1 hour ago"

# Export logs to file
sudo journalctl -u social-media-agent > logs.txt
```

### Database Backup

```bash
# Backup database
cp ~/Social-Media-Agent/social_media_agent.db ~/backup_$(date +%Y%m%d).db

# Automated backup script
cat > ~/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/database_backups
mkdir -p $BACKUP_DIR
cp ~/Social-Media-Agent/social_media_agent.db \
   $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).db
# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.db" -mtime +7 -delete
EOF

chmod +x ~/backup_db.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * ~/backup_db.sh") | crontab -
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs for errors
sudo journalctl -u social-media-agent -n 50

# Common issues:
# 1. Missing .env file
ls -la ~/Social-Media-Agent/.env

# 2. Invalid Python path
which python3
~

/Social-Media-Agent/.venv/bin/python3 --version

# 3. Port already in use
sudo lsof -i :8000
```

### Database Errors

```bash
# Check database permissions
ls -la ~/Social-Media-Agent/social_media_agent.db

# Reinitialize database
cd ~/Social-Media-Agent
source .venv/bin/activate
python3 -c "from src.database import init_db; init_db()"
```

### API Not Accessible

```bash
# Check if service is running
sudo systemctl status social-media-agent

# Check if port is listening
sudo netstat -tulpn | grep 8000

# Check firewall
sudo ufw status
gcloud compute firewall-rules list | grep 8000

# Test locally first
curl http://localhost:8000/health
```

### Scheduler Not Running

```bash
# Check scheduler status
curl http://localhost:8000/health | jq '.scheduler'

# View scheduler logs
sudo journalctl -u social-media-agent | grep scheduler

# Manually reload schedules
curl -X POST http://localhost:8000/api/schedules/1/enable
```

---

## Security Best Practices

1. **Never commit `.env` file to git**
   ```bash
   # Verify .env is in .gitignore
   git check-ignore .env
   ```

2. **Restrict API access**
   - Use firewall rules to limit access by IP
   - Implement API key authentication for production

3. **Regular updates**
   ```bash
   # Update system packages
   sudo apt-get update && sudo apt-get upgrade
   
   # Update Python dependencies
   cd ~/Social-Media-Agent
   uv sync --upgrade
   ```

4. **Monitor logs for suspicious activity**
   ```bash
   sudo journalctl -u social-media-agent | grep -i "error\|failed\|unauthorized"
   ```

5. **Use HTTPS in production**
   - Set up SSL certificate (Let's Encrypt)
   - Configure Nginx with HTTPS

---

## Performance Optimization

### For High-Volume Usage

1. **Use PostgreSQL instead of SQLite**
   ```env
   DATABASE_URL=postgresql://user:pass@localhost/socialmedia
   ```

2. **Add Redis for caching**
3. **Increase worker processes**
   ```bash
   # Edit systemd service
   ExecStart=... --workers 4 --worker-class uvicorn.workers.UvicornWorker
   ```

4. **Enable database connection pooling**
5. **Set up load balancing with multiple instances**

---

## Support

For issues or questions:
- Check logs: `sudo journalctl -u social-media-agent -f`
- Review API docs: http://YOUR_VM_IP:8000/docs
- Test endpoints with Swagger UI

---

## Summary Checklist

- [ ] VM created and accessible via SSH
- [ ] Code deployed to VM
- [ ] Setup script executed successfully
- [ ] `.env` file configured with actual API keys
- [ ] Database initialized
- [ ] Service started and enabled
- [ ] Firewall rules configured
- [ ] Health check passing
- [ ] Test post created successfully
- [ ] Schedule created and running
- [ ] Logs monitored for errors
- [ ] Backup strategy in place

Once all items are checked, your Social Media Agent is fully deployed and operational!
