#!/bin/bash
# Crowscap AWS EC2 Server Setup Script
# Run this ONCE on your AWS EC2 instance after SSH'ing in

set -e

echo "🚀 Crowscap AWS Server Setup"
echo "=============================="
echo ""

# Step 1: Update system packages
echo "[1/8] Updating system packages..."
sudo yum update -y

# Step 2: Install dependencies
echo "[2/8] Installing Python, PostgreSQL, and development tools..."
sudo yum install -y python3 python3-pip postgresql15 postgresql15-server postgresql15-contrib git gcc postgresql15-devel openssl-devel libffi-devel bzip2-devel readline-devel zlib-devel

# Step 3: Initialize Python virtual environment
echo "[3/8] Setting up Python virtual environment..."
cd ~/crowscap-backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]" || pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic pydantic pydantic-settings openai jinja2 python-multipart redis asyncpg aiohttp

# Step 4: Start PostgreSQL
echo "[4/8] Starting PostgreSQL..."
sudo /usr/pgsql-15/bin/pg_ctl -D /var/lib/pgsql/data/ -l /var/lib/pgsql/data/logfile start
sudo systemctl enable postgresql-15
sudo systemctl start postgresql-15

# Step 5: Create database and user (PROMPT FOR PASSWORD!)
echo "[5/8] Setting up database..."
read -s -p "Enter database password for crowscap_user (or leave blank for no password): " DB_PASSWORD
echo ""

if [ -z "$DB_PASSWORD" ]; then
    # No password (not recommended for production)
    sudo -u postgres psql -c "CREATE DATABASE crowscap_prod;" 2>/dev/null || true
    sudo -u postgres psql -c "DROP USER IF EXISTS crowscap_user;" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE USER crowscap_user;" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE crowscap_prod TO crowscap_user;" 2>/dev/null || true
else
    sudo -u postgres psql -c "CREATE DATABASE crowscap_prod;" 2>/dev/null || true
    sudo -u postgres psql -c "DROP USER IF EXISTS crowscap_user;" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE USER crowscap_user WITH PASSWORD '$DB_PASSWORD';"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE crowscap_prod TO crowscap_user;"
fi

# Enable pgvector extension
sudo -u postgres psql -d crowscap_prod -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true

# Grant schema permissions
sudo -u postgres psql -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO crowscap_user;" 2>/dev/null || true

# Step 6: Update environment file with actual credentials
echo "[6/8] Configuring environment variables..."
cd ~/crowscap-backend
sed -i "s|your_password_here|$DB_PASSWORD|g" .env.production 2>/dev/null || echo "# Password needs manual update"

# Step 7: Initialize database
echo "[7/8] Initializing database..."
source .venv/bin/activate
python scripts/init_db.py 2>/dev/null || {
    echo "Database initialization may need manual intervention"
}

# Step 8: Set up systemd service
echo "[8/8] Setting up systemd service..."
sudo cp ~/crowscap.service /etc/systemd/system/crowscap.service
sudo sed -i "s|/home/ec2-user|$(whoami)|g" /etc/systemd/system/crowscap.service
sudo systemctl daemon-reload
sudo systemctl enable crowscap
echo ""

echo "========================================="
echo "✅ Server setup complete!"
echo ""
echo "📋 IMPORTANT NEXT STEPS:"
echo "1. Edit ~/.crowscap-backend/.env.production and update these secrets:"
echo "   - DASHSCOPE_API_KEY (your Qwen Cloud API key)"
echo "   - CROWSCAP_JWT_SECRET (generate a random 32+ char string)"
echo "   - GOOGLE_CLIENT_ID, etc."
echo ""
echo "2. Open AWS Security Group ports:"
echo "   - 8000/TCP (API)"
echo "   - 80/TCP (HTTP via Nginx)"
echo "   - 443/TCP (HTTPS via Nginx)"
echo ""
echo "3. Start the application:"
echo "   sudo systemctl start crowscap"
echo ""
echo "4. Check status:"
echo "   sudo systemctl status crowscap"
echo "   tail -f /var/log/crowscap.log"
echo ""
echo "5. Test health endpoint:"
echo "   curl https://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/api/v1/health"
echo ""
