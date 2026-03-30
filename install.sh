#!/bin/bash
# Kimmy Scalper Installation Script
# One-command setup for elite crypto trading

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           🚀 KIMMY SCALPER v2.0 INSTALLER                 ║"
echo "║       Elite Ultra-Low Latency Crypto Trading               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

BASE_DIR="/root/.openclaw/workspace/KIMMY_SCALPER"
cd "$BASE_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${YELLOW}[1/8] Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
if [ -z "$PYTHON_VERSION" ]; then
    echo -e "${RED}✗ Python 3 not found!${NC}"
    exit 1
fi

if [ "$(printf '%s\n' "3.10" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.10" ]; then
    echo -e "${RED}✗ Python 3.10+ required (found $PYTHON_VERSION)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION detected${NC}"

# Install system packages
echo -e "${YELLOW}[2/8] Installing system dependencies...${NC}"
apt-get update -qq
apt-get install -y -qq python3-dev python3-pip git curl htop screen tmux build-essential wget

# Install TA-Lib C library
echo -e "${YELLOW}[3/8] Installing TA-Lib C library...${NC}"
if [ ! -f "/usr/local/lib/libta_lib.so" ]; then
    cd /tmp
    wget -q http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
    tar -xzf ta-lib-0.4.0-src.tar.gz
    cd ta-lib
    ./configure --prefix=/usr/local >/dev/null 2>&1
    make -j$(nproc) >/dev/null 2>&1
    make install >/dev/null 2>&1
    ldconfig
    echo -e "${GREEN}✓ TA-Lib installed${NC}"
else
    echo -e "${GREEN}✓ TA-Lib already installed${NC}"
fi

# Create directories
echo -e "${YELLOW}[4/8] Creating directory structure...${NC}"
mkdir -p "$BASE_DIR"/{data,logs,config}
for dir in strategies engine ui backtest agents; do
    mkdir -p "$BASE_DIR/$dir"
    touch "$BASE_DIR/$dir/__init__.py"
done
echo -e "${GREEN}✓ Directories created${NC}"

# Install Python packages
echo -e "${YELLOW}[5/8] Installing Python packages...${NC}"
python3 -m pip install --upgrade pip -q

pip3 install -q \
    textual==0.52.1 \
    rich==13.7.0 \
    ccxt==4.2.0 \
    websockets==12.0 \
    pandas==2.1.4 \
    numpy==1.26.3 \
    pyyaml==6.0.1 \
    schedule==1.2.0 \
    python-dotenv==1.0.0

# Install TA-Lib Python wrapper
pip3 install -q TA-Lib==0.4.28

echo -e "${GREEN}✓ Python packages installed${NC}"

# Set permissions
echo -e "${YELLOW}[6/8] Setting permissions...${NC}"
chmod -R 755 "$BASE_DIR"
chmod +x "$BASE_DIR/run.sh" 2>/dev/null || true
echo -e "${GREEN}✓ Permissions set${NC}"

# Create systemd service
echo -e "${YELLOW}[7/8] Creating systemd service...${NC}"
cat > /etc/systemd/system/kimmy-scalper.service << EOF
[Unit]
Description=Kimmy Scalper - Elite Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$BASE_DIR
Environment=PYTHONPATH=$BASE_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 $BASE_DIR/main.py --paper
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo -e "${GREEN}✓ Service created${NC}"

# Verify installation
echo -e "${YELLOW}[8/8] Verifying installation...${NC}"
python3 -c "import textual; import ccxt; import pandas; import numpy; import talib" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All packages verified${NC}"
else
    echo -e "${RED}✗ Package verification failed${NC}"
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✅ INSTALLATION COMPLETE                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "  1. Start paper trading:"
echo "     cd $BASE_DIR"
echo "     python3 main.py --paper"
echo ""
echo "  2. Run as service:"
echo "     systemctl start kimmy-scalper"
echo "     systemctl enable kimmy-scalper"
echo ""
echo "  3. View logs:"
echo "     journalctl -u kimmy-scalper -f"
echo ""
echo "  4. For live trading (after 48h profitable paper):"
echo "     python3 main.py --live"
echo ""
echo "Location: $BASE_DIR"
echo ""
echo "Built by Kimmy 🚀"
echo ""
