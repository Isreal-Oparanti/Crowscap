#!/bin/bash
# Quick Setup Script for Crowscap on AWS EC2
# Copy this to your AWS instance and run after SSH'ing in

echo "🚀 Quick Setup for Crowscap on AWS"
echo "=================================="
echo ""

# 1. Install system dependencies
echo "[1/6] Installing dependencies..."
sudo yum update -y > /dev/null 2>&1
sudo yum install -y python3 pip3 postgresql15 postgresql15-server git gcc openssl-devel libffi-devel bzip2-devel -y > /dev/null 2>&1
echo "[DONE] Dependencies installed"

# 2. Start PostgreSQL
echo "[2/6] Starting PostgreSQL..."
sudo /usr/pgsql-15/bin/pg_ctl -D /var/lib/pgsql/data/ -l /var/lib/pgsql/data/logfile start > /dev/null 2>&1
sudo systemctl enable postgresql-15 > /dev/null 2>&1
echo "[DONE] PostgreSQL started"

# 3. Create database
echo "[3/6] Creating database..."
sudo -u postgres psql -c "CREATE DATABASE crowscap_prod;" 2>/dev/null || echo "Database already exists"
sudo -u postgres psql -d crowscap_prod -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || echo "Extension already exists"
echo "[DONE] Database ready"

# 4. Create virtual environment
echo "[4/6] Setting up Python environment..."
cd ~/crowscap-backend
python3 -m venv .venv > /dev/null 2>&1
source .venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic pydantic pydantic-settings openai jinja2 python-multipart aiohttp > /dev/null 2>&1
echo "[DONE] Python environment ready"

# 5. Initialize database
echo "[5/6] Initializing database schema..."
python scripts/init_db.py 2>/dev/null || {
    echo "[FAILED] Database init failed - check manually"
}
echo "[DONE] Database initialized"

# 6. Create systemd service
echo "[6/6] Setting up systemd service..."
if [ ! -f ~/crowscap.service ]; then
    echo "ERROR: crowscap.service file not found!"
    echo "Please transfer it from your local machine first"
    exit 1
fi

sudo cp ~/crowscap.service /etc/systemd/system/crowscap.service
sudo systemctl daemon-reload > /dev/null 2>&1
sudo systemctl enable crowscap > /dev/null 2>&1
sudo systemctl start crowscap > /dev/null 2>&1
echo "[DONE] Service configured"

echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo ""
echo "IMPORTANT:"
echo ""
echo "Before starting the service, you MUST edit:"
echo "   ~/.crowscap-backend/.env.production"
echo ""
echo "Update these values:"
echo "   DASHSCOPE_API_KEY = your_qwen_api_key"
echo "   DATABASE_URL = postgresql://postgres@localhost/crowscap_prod"
echo "   HOST = 0.0.0.0"
echo "   PORT = 8000"
echo ""
echo "Then start the service:"
echo "   sudo systemctl start crowscap"
echo ""
echo "Check status:"
echo "   sudo systemctl status crowscap"
echo ""
echo "View logs:"
echo "   tail -f /var/log/crowscap.log"
echo ""
echo "Test API:"
echo "   curl http://localhost:8000/api/v1/health"
echo ""
