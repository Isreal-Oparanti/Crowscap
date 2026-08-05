# Crowscap AWS Migration Guide

## Overview
This guide will help you migrate your Crowscap backend from Qwen Cloud to your AWS EC2 instance (54.160.242.246).

## Quick Start (All-in-One)

### Step 1: Transfer Files to AWS

**Option A: Manual SCP/SFTP**
```bash
cd ~/Downloads
chmod 400 crowscap-aws.pem

# Copy entire backend folder
scp -r -i crowscap-aws.pem \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.db' \
    --exclude='.git' \
    Backend/ ec2-user@54.160.242.246:~/crowscap-backend/

# Copy config files
scp -i crowscap-aws.pem crowscap.service ec2-user@54.160.242.246:~/
scp -i crowscap-aws.pem nginx-crowscap.conf ec2-user@54.160.242.246:~/
scp -i crowscap-aws.pem .env.production ec2-user@54.160.242.246:~/
```

**Option B: Git Clone on Server**
```bash
ssh -i crowscap-aws.pem ec2-user@54.160.242.246
mkdir -p ~/crowscap-backend
cd ~/crowscap-backend
git clone YOUR_GITHUB_REPO_URL .
```

### Step 2: SSH into Your Instance
```bash
ssh -i ~/Downloads/crowscap-aws.pem ec2-user@54.160.242.246
```

### Step 3: Run Server Setup
```bash
cd ~/crowscap-backend

# Install dependencies
sudo yum update -y
sudo yum install -y python3-pip postgresql15 postgresql15-server git gcc openssl-devel libffi-devel bzip2-devel

# Create database
sudo /usr/pgsql-15/bin/pg_ctl -D /var/lib/pgsql/data/ -l /var/lib/pgsql/data/logfile start
sudo systemctl enable postgresql-15

sudo -u postgres psql -c "CREATE DATABASE crowscap_prod;"
sudo -u postgres psql -c "CREATE EXTENSION vector;"
```

### Step 4: Configure Environment
Edit `.env.production`:
```bash
nano .env.production
```

Update these values:
```ini
DATABASE_URL=postgresql://postgres@localhost/crowscap_prod
DASHSCOPE_API_KEY=your_actual_qwen_api_key
HOST=0.0.0.0
PORT=8000
```

### Step 5: Install Python Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic pydantic pydantic-settings openai jinja2 python-multipart aiohttp
```

### Step 6: Initialize Database
```bash
python scripts/init_db.py
```

### Step 7: Set Up Systemd Service
```bash
sudo cp ~/crowscap.service /etc/systemd/system/crowscap.service
sudo systemctl daemon-reload
sudo systemctl enable crowscap
sudo systemctl start crowscap
```

### Step 8: Configure Firewall (AWS Console)

Go to **EC2 Dashboard → Instances → Select your instance → Security Groups**

Add Inbound Rules:
| Type | Protocol | Port Range | Source |
|------|----------|------------|--------|
| Custom TCP | TCP | 8000 | 0.0.0.0/0 |
| HTTP | TCP | 80 | 0.0.0.0/0 |
| HTTPS | TCP | 443 | 0.0.0.0/0 |
| SSH | TCP | 22 | Your IP Only |

### Step 9: Test Your Deployment
```bash
# Check service status
sudo systemctl status crowscap

# View logs
tail -f /var/log/crowscap.log

# Test health endpoint
curl http://54.160.242.246:8000/api/v1/health
```

### Optional: Set Up Nginx Reverse Proxy
```bash
sudo yum install -y nginx
sudo cp ~/nginx-crowscap.conf /etc/nginx/conf.d/crowscap.conf
sudo systemctl enable nginx
sudo systemctl start nginx
```

## Security Checklist

Before going live:

- [ ] Change `CROWSCAP_ADMIN_PASSWORD` in `.env.production`
- [ ] Generate secure `CROWSCAP_JWT_SECRET` (32+ random chars)
- [ ] Update Google OAuth credentials (`GOOGLE_CLIENT_ID`, etc.)
- [ ] Restrict SSH access to your IP only in AWS Security Group
- [ ] Enable HTTPS with Let's Encrypt (optional but recommended)
- [ ] Set up monitoring/alerts (CloudWatch, Sentry, etc.)
- [ ] Configure database backups (RDS snapshots or manual)

## Monitoring

### Logs
```bash
# Application logs
journalctl -u crowscap -f

# Error logs
tail -f /var/log/crowscap-error.log

# Nginx logs (if configured)
tail -f /var/log/nginx/error.log
```

### Performance Tuning (Optional)
```bash
# Increase file descriptor limit
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf

# Optimize PostgreSQL
sudo nano /etc/postgresql*/*/main/postgresql.conf
# Add: shared_buffers = 2GB, effective_cache_size = 6GB, etc.
```

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u crowscap -n 50 --no-pager
# Check for configuration errors
```

### Database connection failed
```bash
# Verify PostgreSQL is running
sudo systemctl status postgresql-15

# Test connection locally
sudo -u postgres psql -c "SELECT 1;"
```

### Memory issues
Reduce worker count in `crowscap.service`:
```ini
ExecStart=/home/ec2-user/crowscap-backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

## Next Steps

1. Update your mobile app's API base URL to point to `https://54.160.242.246/api/v1` or your custom domain
2. Set up monitoring (AWS CloudWatch, Sentry, DataDog)
3. Configure automated backups
4. Consider using RDS (managed PostgreSQL) instead of self-managed for production
5. Set up SSL certificate with Let's Encrypt

---

**Need Help?** Check the existing docs in `/docs/` folder or contact support@crowscap.xyz
