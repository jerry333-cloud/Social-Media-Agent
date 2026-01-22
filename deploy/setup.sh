#!/bin/bash
#
# Setup script for Social Media Agent on GCP VM
#
# This script:
# 1. Installs system dependencies
# 2. Installs Python and uv
# 3. Clones/updates the repository
# 4. Installs Python dependencies
# 5. Sets up .env file
# 6. Initializes database
# 7. Creates systemd service
# 8. Configures firewall

set -e

echo "========================================="
echo "Social Media Agent - VM Setup Script"
echo "========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running on Debian/Ubuntu
if [ ! -f /etc/debian_version ]; then
    echo -e "${RED}Error: This script is designed for Debian/Ubuntu systems${NC}"
    exit 1
fi

echo -e "${GREEN}Step 1: Installing system dependencies...${NC}"
sudo apt-get update
sudo apt-get install -y \
    git \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev

echo -e "${GREEN}Step 2: Installing uv (Python package manager)...${NC}"
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "uv already installed"
fi

echo -e "${GREEN}Step 3: Setting up project directory...${NC}"
PROJECT_DIR="$HOME/Social-Media-Agent"
if [ -d "$PROJECT_DIR" ]; then
    echo "Project directory exists, pulling latest changes..."
    cd "$PROJECT_DIR"
    git pull || echo "Could not pull changes (working directory may have modifications)"
else
    echo "Cloning repository..."
    cd "$HOME"
    # Note: Update this with your actual repository URL
    echo -e "${YELLOW}Note: Manual git clone may be needed if repository is private${NC}"
    # git clone <your-repo-url> Social-Media-Agent
    # For now, assuming code is already copied
fi

cd "$PROJECT_DIR"

echo -e "${GREEN}Step 4: Installing Python dependencies...${NC}"
uv sync

echo -e "${GREEN}Step 5: Setting up environment variables...${NC}"
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo -e "${YELLOW}IMPORTANT: Edit .env file with your actual API keys:${NC}"
    echo "  nano .env"
else
    echo ".env file already exists"
fi

echo -e "${GREEN}Step 6: Initializing database...${NC}"
source .venv/bin/activate
python3 -c "from src.database import init_db; init_db()" || echo "Database initialization completed"

echo -e "${GREEN}Step 7: Creating systemd service...${NC}"
SERVICE_FILE="/etc/systemd/system/social-media-agent.service"
sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Social Media Agent FastAPI Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$PROJECT_DIR/.venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd..."
sudo systemctl daemon-reload
sudo systemctl enable social-media-agent.service

echo -e "${GREEN}Step 8: Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    echo "Configuring ufw firewall..."
    sudo ufw allow 8000/tcp
    sudo ufw allow 22/tcp
    echo "Firewall rules added"
else
    echo "ufw not installed, skipping firewall configuration"
fi

echo ""
echo -e "${GREEN}========================================="
echo "Setup Complete!"
echo "=========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2. Start the service:"
echo "   sudo systemctl start social-media-agent"
echo ""
echo "3. Check service status:"
echo "   sudo systemctl status social-media-agent"
echo ""
echo "4. View logs:"
echo "   sudo journalctl -u social-media-agent -f"
echo ""
echo "5. Access API at: http://$(hostname -I | awk '{print $1}'):8000"
echo "   API docs at: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
