#!/bin/bash
#
# Stop all running scrapers
#

set -e

echo "🛑 Stopping GitHub Scrapers"
echo "============================"
echo ""

# Function to stop scraper
stop_scraper() {
    local pid_file=$1
    local scraper_name=$(basename "$pid_file" .pid)
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo "⏹️  Stopping $scraper_name (PID: $pid)"
            kill $pid 2>/dev/null || true
            sleep 1
            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                echo "   Force stopping..."
                kill -9 $pid 2>/dev/null || true
            fi
        else
            echo "⚠️  $scraper_name not running (PID: $pid)"
        fi
        rm "$pid_file"
    fi
}

# Stop all scrapers
if [ -d "logs" ]; then
    for pid_file in logs/*.pid; do
        if [ -f "$pid_file" ]; then
            stop_scraper "$pid_file"
        fi
    done
fi

echo ""
echo "✅ All scrapers stopped"
echo ""
