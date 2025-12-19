# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your GitHub tokens:
```
GITHUB_TOKEN=ghp_your_token_here
GITHUB_TOKEN_1=ghp_second_token_here
```

### Step 3: Start Database

**Option A: Use existing Docker setup**
```bash
docker compose up -d
```

**Option B: Use new Docker setup**
```bash
docker compose -f docker/docker-compose.yml up postgres -d
```

### Step 4: Migrate Database (if you have existing data)

```bash
python migrate_database.py
```

### Step 5: Run Scrapers

**Run individually:**
```bash
# Collect usernames
python scripts/run_username_scraper.py

# Enrich profiles
python scripts/run_profile_scraper.py

# Enrich social media (placeholder)
python scripts/run_social_scraper.py
```

**Run on schedule:**
```bash
python scripts/run_scheduler.py
```

## 🐳 Docker Commands

### Local Development

```bash
# Start database only
docker compose -f docker/docker-compose.yml up postgres -d

# Run username scraper
docker compose -f docker/docker-compose.yml --profile username up

# Run profile scraper
docker compose -f docker/docker-compose.yml --profile profile up

# Run scheduler
docker compose -f docker/docker-compose.yml --profile scheduler up

# Stop all
docker compose -f docker/docker-compose.yml down
```

### Production (with RDS)

```bash
# Set environment variables
export DB_HOST=your-rds-endpoint.amazonaws.com
export DB_NAME=github_developers
export DB_USER=your_user
export DB_PASSWORD=your_password

# Run scraper
docker compose -f docker/docker-compose.prod.yml up username_scraper

# Or run scheduler
docker compose -f docker/docker-compose.prod.yml up scheduler
```

## 📊 Check Status

```bash
# Connect to database
docker exec -it github_scraper_db psql -U ahmed -d github_developers

# Or if using production
psql -h your-rds-endpoint -U your_user -d github_developers
```

```sql
-- Status distribution
SELECT enrichment_status, COUNT(*) 
FROM developers 
GROUP BY enrichment_status;

-- Recent entries
SELECT username, enrichment_status, scraped_at 
FROM developers 
ORDER BY scraped_at DESC 
LIMIT 10;
```

## ⚙️ Configuration

Edit `src/config/settings.py` to change:
- Target cities and date ranges
- Batch sizes and intervals
- Retry logic and delays
- Scheduler timings

## 🔧 Troubleshooting

**Rate limit errors:**
- Add more GitHub tokens in `.env`
- Increase `TOKEN_ROTATION_DELAY` in settings

**Database connection errors:**
- Check PostgreSQL is running
- Verify credentials in `.env`
- For RDS, check security groups

**Import errors:**
- Make sure you're in project root
- Run: `export PYTHONPATH=/home/moez/clients/alexander/github-scrapper-`

## 📈 Next Steps

1. Monitor the scrapers with logs
2. Check metrics with `metrics.print_summary()`
3. Implement social scraper logic in `src/scrapers/social_scraper.py`
4. Add tests in `tests/` directory
5. Set up production deployment on EC2/ECS
