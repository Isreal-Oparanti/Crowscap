#!/bin/bash
# Crowscap AWS EC2 Deployment Script
# Run this on your local machine to prepare deployment
# Then transfer files to AWS and run server-setup.sh

set -e

AWS_IP="${1:-54.160.242.246}"
SSH_KEY="${2:-~/Downloads/crowscap-aws.pem}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Crowscap AWS Deployment Script"
echo "=================================="
echo "Target: $AWS_IP"
echo "Key: $SSH_KEY"
echo ""

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found at: $SSH_KEY"
    exit 1
fi

# Create remote directory
echo "📦 Creating remote directory..."
ssh -i "$SSH_KEY" ec2-user@"$AWS_IP" "mkdir -p ~/crowscap-backend"

# Transfer backend code via SCP (excluding large directories)
echo "📤 Transferring backend code..."
scp -r -i "$SSH_KEY" \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.db' \
    --exclude='.pytest_cache' \
    --exclude='.git' \
    --exclude='node_modules' \
    "$PROJECT_ROOT/backend/" ec2-user@"$AWS_IP":~/crowscap-backend/

# Transfer environment file (prompt user for secrets first!)
echo "⚠️  You need to update .env.production with your actual secrets before proceeding!"
echo "   Edit: $PROJECT_ROOT/backend/.env.production"
read -p "Press Enter when you've updated the .env.production file..."

scp -i "$SSH_KEY" "$PROJECT_ROOT/backend/.env.production" ec2-user@"$AWS_IP":~/crowscap-backend/

# Transfer server setup script
echo "📜 Transferring server-setup.sh..."
scp -i "$SSH_KEY" "$PROJECT_ROOT/aws-server-setup.sh" ec2-user@"$AWS_IP":~/

# Transfer systemd service
echo "🛠️  Transferring crowscap.service..."
scp -i "$SSH_KEY" "$PROJECT_ROOT/crowscap.service" ec2-user@"$AWS_IP":~/

# Transfer nginx config
echo "🌐 Transferring nginx config..."
scp -i "$SSH_KEY" "$PROJECT_ROOT/nginx-crowscap.conf" ec2-user@"$AWS_IP":~/

echo ""
echo "✅ Files transferred successfully!"
echo ""
echo "Next steps:"
echo "1. SSH into your instance: ssh -i $SSH_KEY ec2-user@$AWS_IP"
echo "2. Run the setup script: ./server-setup.sh"
echo "3. Update firewall rules in AWS Console"
echo "4. Access your API at: https://$AWS_IP/api/v1/health"
echo ""
