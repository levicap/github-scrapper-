#!/bin/bash
#
# Run GitHub Scraper with Multiple Instances
# Usage: ./run_scrapers.sh
#

set -e

echo "🚀 Starting GitHub Scraper with Multiple Instances"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your GitHub tokens"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check database connection
echo -e "${BLUE}📊 Checking database connection...${NC}"
if ! PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c '\q' 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Database not reachable. Make sure PostgreSQL is running.${NC}"
    echo ""
    echo "Start PostgreSQL with Docker:"
    echo "  docker run -d --name postgres_github -p 5432:5432 \\"
    echo "    -e POSTGRES_DB=$DB_NAME \\"
    echo "    -e POSTGRES_USER=$DB_USER \\"
    echo "    -e POSTGRES_PASSWORD=$DB_PASSWORD \\"
    echo "    postgres:16"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create logs directory
mkdir -p logs

# Function to run scraper in background
run_scraper() {
    local scraper_name=$1
    local instance_num=$2
    local log_file="logs/${scraper_name}_${instance_num}.log"
    
    echo -e "${GREEN}▶️  Starting ${scraper_name} #${instance_num}${NC}"
    
    nohup python "scripts/run_${scraper_name}.py" \
        > "$log_file" 2>&1 &
    
    echo $! > "logs/${scraper_name}_${instance_num}.pid"
    echo "   PID: $! | Log: $log_file"
}

# Start scrapers
echo ""
echo -e "${BLUE}🔍 Starting Username Scraper (1 instance)${NC}"
run_scraper "username_scraper" 1

echo ""
echo -e "${BLUE}👤 Starting Profile Scrapers (2 instances)${NC}"
run_scraper "profile_scraper" 1
sleep 2  # Stagger start slightly
run_scraper "profile_scraper" 2

echo ""
echo "=================================================="
echo -e "${GREEN}✅ All scrapers started!${NC}"
echo ""
echo "📊 Monitor progress:"
echo "  - Tail username scraper: tail -f logs/username_scraper_1.log"
echo "  - Tail profile scraper #1: tail -f logs/profile_scraper_1.log"
echo "  - Tail profile scraper #2: tail -f logs/profile_scraper_2.log"
echo ""
echo "🛑 Stop all scrapers:"
echo "  ./stop_scrapers.sh"
echo ""
echo "📈 Database statistics:"
echo "  python scripts/show_stats.py"
echo ""
