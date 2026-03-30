#!/bin/bash
# Kimmy Scalper - Quick Launch Script

cd /root/.openclaw/workspace/KIMMY_SCALPER

# Check if already running
if pgrep -f "python3 main.py" > /dev/null; then
    echo "⚠️  Kimmy Scalper is already running!"
    echo "Use: kill $(pgrep -f 'python3 main.py')"
    exit 1
fi

# Parse args
MODE="--paper"
if [ "$1" == "live" ]; then
    MODE="--live"
fi

# Launch
echo "🚀 Starting Kimmy Scalper..."
python3 main.py $MODE
