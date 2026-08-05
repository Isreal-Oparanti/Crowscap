# Crowscap AWS Deployment Checklist

## Before Starting (Local Machine)
- [ ] Backend code is committed to Git: `git add . && git commit -m "Prepare for AWS"`
- [ ] `.env.production` file has been created with your secrets
- [ ] SSH key `crowscap-aws.pem` is in `~/Downloads/`
- [ ] Security Group access configured on AWS Console (Port 22 for SSH, 8000 for API)

## Step 1: Transfer Files to AWS (from local machine)
```bash
cd ~/Downloads
chmod 400 crowscap-aws.pem

# Option A: SCP entire backend folder
scp -r -i crowscap-aws.pem \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.db' \
    --exclude='.git' \
    ec2-user@54.160.242.246:/home/ec2-user/crowscap-backend/

# Copy config files
scp -i crowscap-aws.pem ../crowscap/crowscap.service ec2-user@54.160.242.246:~/
scp -i crowscap-aws.pem ../crowscap/nginx-crowscap.conf ec2-user@54.160.242.246:~/
scp -i crowscap-aws.pem ../crowscap/.env.production ec2-user@54.160.242.246:~/
scp -i crowscap-aws.pem ../crowscap/quick-setup.sh ec2-user@54.160.242.246:~/
```

## Step 2: Connect to AWS EC2
```bash
ssh -i crowscap-aws.pem ec2-user@54.160.242.246
```

## Step 3: Run Quick Setup
```bash
cd ~/
chmod +x quick-setup.sh
./quick-setup.sh
```

## Step 4: Configure Environment Variables
Edit the `.env.production` file with YOUR actual secrets:
```bash
cd ~/crowscap-backend
nano .env.production
```

**Must update these:**
- `DASHSCOPE_API_KEY=` → Your Qwen Cloud API key
- `DATABASE_URL=` → `postgresql://postgres@localhost/crowscap_prod`
- `HOST=0.0.0.0` → Keep as is
- `PORT=8000` → Keep as is
- `CROWSCAP_ADMIN_PASSWORD=` → Generate secure password
- `CROWSCAP_JWT_SECRET=` → 32+ random characters (use `openssl rand -hex 32`)
- Google OAuth credentials if using authentication

## Step 5: Start the Service
```bash
sudo systemctl start crowscap
sudo systemctl status crowscap
```

## Step 6: Test the API
```bash
# Health check
curl http://localhost:8000/api/v1/health

# From your local machine (replace IP):
curl http://54.160.242.246:8000/api/v1/health
```

Expected response:
```json
{
  "name": "Crowscap API",
  "status": "ok",
  "docs": "/docs"
}
```

## Step 7: Configure Firewall (AWS Console)

Go to: **EC2 Dashboard → Instances → Select your instance → Actions → Network & Security → Edit Security Groups**

### Inbound Rules to Add:
| Type | Protocol | Port | Source | Description |
|------|----------|------|--------|-------------|
| Custom TCP | TCP | 8000 | 0.0.0.0/0 | Crowscap API |
| HTTP | TCP | 80 | 0.0.0.0/0 | Nginx (optional) |
| HTTPS | TCP | 443 | 0.0.0.0/0 | Nginx SSL (optional) |
| SSH | TCP | 22 | YOUR_IP_ONLY | Admin access |

## Optional: Set Up Nginx Reverse Proxy
```bash
sudo yum install -y nginx
sudo cp ~/nginx-crowscap.conf /etc/nginx/conf.d/crowscap.conf
sudo systemctl enable nginx
sudo systemctl start nginx
```

Test with port 80:
```bash
curl http://54.160.242.246/api/v1/health
```

## Verification Checklist
- [ ] API responds to health check
- [ ] Service is running: `sudo systemctl status crowscap` shows active
- [ ] Logs are clean: `tail -f /var/log/crowscap.log` shows no errors
- [ ] Database accessible: Can run queries via psql
- [ ] Qwen API connectivity working (check logs for successful calls)
- [ ] Mobile app can connect (update BASE_URL in mobile app)

## Post-Deployment Tasks
- [ ] Update mobile app's API endpoint to point to your AWS IP or domain
- [ ] Set up automated backups (RDS snapshots or manual pg_dump)
- [ ] Enable logging/monitoring (CloudWatch, Sentry, etc.)
- [ ] Consider upgrading to RDS PostgreSQL for production reliability
- [ ] Set up Let's Encrypt SSL certificate (certbot)
- [ ] Document any custom configurations

## Monitoring Commands

```bash
# Check service status
sudo systemctl status crowscap

# View real-time logs
journalctl -u crowscap -f

# View last 100 lines
journalctl -u crowscap -n 100

# Database connection test
sudo -u postgres psql -c "SELECT 'connection OK';"

# Check disk space
df -h

# Check memory/CPU
top -b -n 1 | head -20
```

## Troubleshooting

### Service not starting
```bash
sudo journalctl -u crowscap -n 100 --no-pager
# Look for configuration errors or missing dependencies
```

### Database connection failed
```bash
# Verify PostgreSQL is running
sudo systemctl status postgresql-15

# Test locally
sudo -u postgres psql -c "SELECT 1;"
```

### Permission denied accessing files
```bash
sudo chown -R ec2-user:ec2-user ~/crowscap-backend
chmod 755 ~/crowscap-backend
```

---

**Need Help?** 
- Check application logs: `/var/log/crowscap.log`
- Review error logs: `/var/log/crowscap-error.log`
- Consult deployment docs in `/docs/` folder
