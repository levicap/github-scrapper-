# 🚀 Quick Start - Running Multiple Scraper Instances

## Prerequisites

1. **PostgreSQL running:**
   ```bash
   docker run -d --name postgres_github -p 5432:5432 \
     -e POSTGRES_DB=github_developers \
     -e POSTGRES_USER=ahmed \
     -e POSTGRES_PASSWORD=ahmed123 \
     postgres:16
   ```

2. **Environment configured:**
   - Copy `.env.example` to `.env`
   - Add your GitHub token(s)

3. **Database initialized:**
   ```bash
   python migrate_database.py
   ```

## Running with 1 Username Scraper + 2 Profile Scrapers

### Method 1: Shell Script (Recommended)

```bash
# Start all scrapers
./run_scrapers.sh

# Monitor logs
tail -f logs/username_scraper_1.log
tail -f logs/profile_scraper_1.log
tail -f logs/profile_scraper_2.log

# Check stats
python scripts/show_stats.py

# Stop all
./stop_scrapers.sh
```

### Method 2: Manual Python (separate terminals)

**Terminal 1 - Username Scraper:**
```bash
python scripts/run_username_scraper.py
```

**Terminal 2 - Profile Scraper #1:**
```bash
python scripts/run_profile_scraper.py
```

**Terminal 3 - Profile Scraper #2:**
```bash
python scripts/run_profile_scraper.py
```

### Method 3: Docker Compose

```bash
# Start services
docker compose -f docker/docker-compose.yml \
  --profile username \
  --profile profile \
  up --scale profile_scraper=2 -d

# View logs
docker compose -f docker/docker-compose.yml logs -f

# Stop services
docker compose -f docker/docker-compose.yml down
```

## Monitoring

### Real-time Statistics
```bash
# Watch stats update every 2 seconds
watch -n 2 python scripts/show_stats.py
```

### Database Queries
```bash
# Connect to database
psql -h localhost -U ahmed -d github_developers

# Check status distribution
SELECT enrichment_status, COUNT(*) 
FROM developers 
GROUP BY enrichment_status;

# See active processing by instance
SELECT claimed_by, COUNT(*) 
FROM developers 
WHERE enrichment_status='PROCESSING' 
GROUP BY claimed_by;

# Check recent activity
SELECT username, enrichment_status, updated_at 
FROM developers 
ORDER BY updated_at DESC 
LIMIT 10;
```

### Log Locations

- Username scraper: `logs/username_scraper_1.log`
- Profile scraper #1: `logs/profile_scraper_1.log`
- Profile scraper #2: `logs/profile_scraper_2.log`

## Parallel Processing Details

### How It Works

1. **Username Scraper** searches GitHub and inserts usernames with `INITIAL` status
2. **Profile Scrapers** (both instances):
   - Claim batches of 50 `INITIAL` records using `FOR UPDATE SKIP LOCKED`
   - Set status to `PROCESSING` with their instance ID
   - Fetch profile data from GitHub
   - Update to `PROFILED` status and release claim
3. **Row-level locking** prevents duplicate processing
4. **Stale claim timeout** (30 min) handles crashed instances

### Scaling

You can scale to any number of instances:

```bash
# Heavy load example
./run_scrapers.sh  # Edit to add more instances

# Or with Docker
docker compose --profile username --profile profile \
  up --scale username_scraper=2 --scale profile_scraper=5 -d
```

## Troubleshooting

### No scrapers starting?
```bash
# Check if processes are running
ps aux | grep python | grep scraper

# Check PIDs
cat logs/*.pid
```

### Database connection issues?
```bash
# Test connection
psql -h localhost -U ahmed -d github_developers -c '\q'

# Check if PostgreSQL is running
docker ps | grep postgres
```

### Rate limit errors?
- Add more GitHub tokens to `.env` (GITHUB_TOKEN_1, GITHUB_TOKEN_2, etc.)
- Tokens automatically rotate when rate limited

### Profile scrapers idle?
- Check if there are `INITIAL` records: `SELECT COUNT(*) FROM developers WHERE enrichment_status='INITIAL';`
- Run username scraper first to populate data

## Expected Performance

- **Username Scraper**: ~1000 usernames/hour (depends on GitHub search API)
- **Profile Scraper**: ~50-100 profiles/hour per instance (depends on tokens & rate limits)
- **With 2 Profile Scrapers**: ~100-200 profiles/hour total

## Next Steps

After scraping completes, analyze your data:

```sql
-- Top developers by followers
SELECT username, followers, location 
FROM developers 
WHERE enrichment_status='PROFILED' 
ORDER BY followers DESC 
LIMIT 20;

-- Most popular programming languages
SELECT language, COUNT(*) as count
FROM repositories
GROUP BY language
ORDER BY count DESC
LIMIT 10;

-- Developers with social media
SELECT COUNT(*) 
FROM social_links 
WHERE platform='twitter';
```
