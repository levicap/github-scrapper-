#!/bin/bash
# 
# Complete setup and run commands
#

echo "🚀 GitHub Scraper - Complete Setup"
echo "=================================="
echo ""

# Step 1: Start PostgreSQL
echo "1️⃣  Starting PostgreSQL..."
docker run -d --name postgres_github -p 5432:5432 \
  -e POSTGRES_DB=github_developers \
  -e POSTGRES_USER=ahmed \
  -e POSTGRES_PASSWORD=ahmed123 \
  postgres:16

echo "   Waiting for PostgreSQL to be ready..."
sleep 5

# Step 2: Create database tables
echo ""
echo "2️⃣  Creating database tables..."
python migrate_database.py

# Step 3: Start scrapers
echo ""
echo "3️⃣  Starting scrapers (1 username + 2 profile)..."
./run_scrapers.sh

echo ""
echo "✅ Setup complete!"
echo ""
echo "📊 Monitor with: python scripts/show_stats.py"
echo "📝 View logs: tail -f logs/*.log"
echo "🛑 Stop all: ./stop_scrapers.sh"
echo ""
