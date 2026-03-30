#!/usr/bin/env python3
"""
Kimmy - Elite Crypto Scalping Bot Setup
One-command installation for Hummingbot v2 + Custom Strategy + Textual Dashboard
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run(cmd, cwd=None):
    print(f"[RUN] {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {result.stderr}")
    return result.returncode == 0

def main():
    base_dir = Path("/root/.openclaw/workspace/KIMMY_SCALPER")
    base_dir.mkdir(exist_ok=True)
    
    print("="*60)
    print("🚀 KIMMY SCALPER - Elite Crypto Trading System Setup")
    print("="*60)
    
    # Step 1: System dependencies
    print("\n[1/7] Installing system dependencies...")
    run("apt-get update && apt-get install -y python3.12 python3.12-dev python3-pip nodejs npm git curl htop screen tmux")
    run("pip3 install --upgrade pip setuptools wheel")
    
    # Step 2: Python dependencies
    print("\n[2/7] Installing Python packages...")
    packages = [
        "hummingbot==2.0.0",
        "textual==0.52.1",
        "rich==13.7.0",
        "ccxt==4.2.0",
        "ccxtpro==1.0.0",
        "websockets==12.0",
        "asyncio-mqtt==0.16.1",
        "pandas==2.1.4",
        "numpy==1.26.3",
        "ta-lib==0.4.28",
        "plotly==5.18.0",
        "pydantic==2.5.3",
        "structlog==23.2.0",
        "python-dotenv==1.0.0",
        "schedule==1.2.0",
        "prometheus-client==0.19.0"
    ]
    run(f"pip3 install {' '.join(packages)}")
    
    # Step 3: Install TA-Lib C library
    print("\n[3/7] Installing TA-Lib C library...")
    if not Path("/usr/local/lib/libta_lib.so").exists():
        run("cd /tmp && wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz")
        run("cd /tmp && tar -xzf ta-lib-0.4.0-src.tar.gz")
        run("cd /tmp/ta-lib && ./configure --prefix=/usr/local && make && make install")
        run("ldconfig")
    
    # Step 4: Create directory structure
    print("\n[4/7] Creating directory structure...")
    dirs = ["strategies", "data", "logs", "config", "ui", "agents", "backtest"]
    for d in dirs:
        (base_dir / d).mkdir(exist_ok=True)
    
    # Step 5: Set permissions
    print("\n[5/7] Setting permissions...")
    run(f"chmod -R 755 {base_dir}")
    
    # Step 6: Create systemd service
    print("\n[6/7] Creating systemd service...")
    service_content = f"""[Unit]
Description=Kimmy Scalper Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={base_dir}
Environment=PYTHONPATH={base_dir}
ExecStart=/usr/bin/python3 {base_dir}/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    with open("/etc/systemd/system/kimmy-scalper.service", "w") as f:
        f.write(service_content)
    run("systemctl daemon-reload")
    
    # Step 7: Create launch script
    print("\n[7/7] Creating launch scripts...")
    launch_script = f"""#!/bin/bash
cd {base_dir}
/usr/bin/python3 main.py "$@"
"""
    with open(f"{base_dir}/launch.sh", "w") as f:
        f.write(launch_script)
    run(f"chmod +x {base_dir}/launch.sh")
    
    print("\n" + "="*60)
    print("✅ Setup Complete!")
    print("="*60)
    print(f"\nLocation: {base_dir}")
    print("\nNext steps:")
    print("  1. Edit config/api_keys.env with your API keys")
    print("  2. Run: python3 main.py --paper")
    print("  3. Or: systemctl start kimmy-scalper")
    print("\nDashboard will be available at: http://localhost:8080")
    print("="*60)

if __name__ == "__main__":
    main()
