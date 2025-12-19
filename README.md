# GitHub Scraper v2.0

A modular, production-ready GitHub user scraper with multi-stage enrichment pipeline and Docker support.

## 🏗️ Architecture

The project uses a **three-stage enrichment pipeline**:

1. **INITIAL** → Username collection (location-based GitHub search)
2. **PROFILED** → Profile enrichment (detailed GitHub data + social links)
3. **ENHANCED** → Social media enrichment (follower counts, verification)

Each stage is handled by an independent scraper that can run separately or on a schedule.

## 📁 Project Structure

```
github-scrapper/
├── src/
│   ├── config/
│   │   └── settings.py          # Configuration constants
│   ├── database/
│   │   ├── models.py             # Database models and enums
│   │   └── repository.py         # Database repository with retry logic
│   ├── scrapers/
│   │   ├── username_scraper.py   # Stage 1: Username collection
│   │   ├── profile_scraper.py    # Stage 2: Profile enrichment
│   │   └── social_scraper.py     # Stage 3: Social enrichment
│   └── utils/
│       ├── logger.py             # Structured logging
│       ├── metrics.py            # Prometheus-style metrics
│       └── github_client.py      # GitHub API client manager
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml        # Local dev with Postgres
│   └── docker-compose.prod.yml   # Production with RDS
├── scripts/
│   ├── run_username_scraper.py
│   ├── run_profile_scraper.py
│   ├── run_social_scraper.py
│   └── run_scheduler.py
├── scheduler.py                  # APScheduler job orchestration
├── requirements.txt
├── .env.example
└── README.md
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone repository
git clone <repo-url>
cd github-scrapper

# Create .env file
cp .env.example .env
# Edit .env with your GitHub tokens and DB credentials

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Locally (Without Docker)

```bash
# Run username scraper
python scripts/run_username_scraper.py

# Run profile scraper
python scripts/run_profile_scraper.py

# Run social scraper
python scripts/run_social_scraper.py

# Run scheduler (all scrapers on schedule)
python scripts/run_scheduler.py
```

### 3. Run with Docker (Local Development)

```bash
# Start PostgreSQL
docker compose -f docker/docker-compose.yml up postgres -d

# Run username scraper
docker compose -f docker/docker-compose.yml --profile username up

# Run profile scraper
docker compose -f docker/docker-compose.yml --profile profile up

# Run scheduler
docker compose -f docker/docker-compose.yml --profile scheduler up
```

### 4. Run with Docker (Production with RDS)

```bash
# Set RDS credentials in .env
export DB_HOST=your-rds-endpoint.amazonaws.com
export DB_NAME=github_developers
export DB_USER=your_user
export DB_PASSWORD=your_password

# Run scrapers
docker compose -f docker/docker-compose.prod.yml up username_scraper
docker compose -f docker/docker-compose.prod.yml up profile_scraper
docker compose -f docker/docker-compose.prod.yml up social_scraper

# Or run scheduler
docker compose -f docker/docker-compose.prod.yml up scheduler
```

## ⚙️ Configuration

All configuration is in [`src/config/settings.py`](src/config/settings.py):

### Scraper Settings

```python
ScraperConfig:
  LOCATIONS: [...]           # Cities to search
  YEARS_START: 2015          # Start year
  YEARS_END: 2025            # End year
  TARGET_USERNAMES: 12000    # Username target
  TARGET_PROFILES: 10000     # Profile target
  MAX_RETRIES: 3             # Retry attempts
  RETRY_DELAY: 5             # Delay between retries
  EXPONENTIAL_BACKOFF: True  # Use exponential backoff
```

### Database Settings

```python
DatabaseConfig:
  HOST: localhost (or RDS endpoint)
  PORT: 5432
  NAME: github_developers
  USER: ahmed
  PASSWORD: ahmed123
```

### Scheduler Settings

```python
SchedulerConfig:
  USE_CRON: False                        # Use intervals instead
  USERNAME_SCRAPER_INTERVAL: 86400       # 24 hours
  PROFILE_SCRAPER_INTERVAL: 86400        # 24 hours
  SOCIAL_SCRAPER_INTERVAL: 86400         # 24 hours
```

## 📊 Database Schema

### `developers` table

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `username` | VARCHAR(255) | GitHub username (unique) |
| `enrichment_status` | ENUM | INITIAL, PROFILED, ENHANCED, FAILED |
| `retry_count` | INTEGER | Number of retry attempts |
| `last_error` | TEXT | Last error message |
| `name`, `email`, `bio`, etc. | Various | GitHub profile data |
| `scraped_at`, `profiled_at`, `enhanced_at` | TIMESTAMP | Timestamps |

### `social_links` table

Stores social media links with platform and verification status.

### `repositories` table

Stores top 5 repositories for each developer.

## 🔄 Enrichment Pipeline

### Stage 1: Username Scraper

- Searches GitHub by location and date ranges
- Saves usernames with `INITIAL` status
- Target: 12,000 usernames

```bash
python scripts/run_username_scraper.py
```

### Stage 2: Profile Scraper

- Reads users with `INITIAL` status
- Fetches detailed GitHub profile data
- Extracts social media links from bio/blog
- Updates status to `PROFILED`
- Target: 10,000 profiles

```bash
python scripts/run_profile_scraper.py
```

### Stage 3: Social Scraper

- Reads users with `PROFILED` status
- Verifies and enriches social media data
- Updates status to `ENHANCED`
- **Note**: Currently a skeleton, implementation pending

```bash
python scripts/run_social_scraper.py
```

## 📈 Metrics

The system tracks metrics for each scraper:

- Total processed
- Success count
- Failure count
- Retry count
- Rate limit hits
- Success rate
- Processing rate (items/hour)

View metrics:
```python
from src.utils import metrics
metrics.print_summary()
```

## 🔧 Retry Logic

- **Max retries**: 3 (configurable)
- **Exponential backoff**: Yes
- **Failed items**: Marked with `FAILED` status
- **Error logging**: Stored in `last_error` column

## 🐳 Docker Deployment

### Local Development

Uses local PostgreSQL container:
```bash
docker compose -f docker/docker-compose.yml up
```

### Production (EC2/ECS with RDS)

Connects to external RDS:
```bash
docker compose -f docker/docker-compose.prod.yml up
```

### Build Image

```bash
docker build -f docker/Dockerfile -t github-scraper:latest .
```

## 📝 Database Migrations

Initial table creation is automatic. For schema changes:

```sql
-- Example: Add new column
ALTER TABLE developers ADD COLUMN new_field VARCHAR(255);

-- Check current status distribution
SELECT enrichment_status, COUNT(*) 
FROM developers 
GROUP BY enrichment_status;
```

## 🔍 Monitoring

### Check Database Stats

```bash
docker exec -it github_scraper_db psql -U ahmed -d github_developers
```

```sql
-- Status distribution
SELECT enrichment_status, COUNT(*) FROM developers GROUP BY enrichment_status;

-- Success rate
SELECT 
  COUNT(CASE WHEN enrichment_status = 'PROFILED' THEN 1 END) as profiled,
  COUNT(CASE WHEN enrichment_status = 'FAILED' THEN 1 END) as failed,
  COUNT(*) as total
FROM developers;
```

### View Logs

```bash
# Docker logs
docker compose logs -f username_scraper

# Local logs (if configured)
tail -f logs/scraper.log
```

## 🚨 Error Handling

- **Rate limits**: Automatic token rotation
- **Network errors**: Retry with exponential backoff
- **Database errors**: Transaction rollback and retry
- **Max retries exceeded**: Mark as `FAILED`, log error

## 🎯 Next Steps

1. **Implement Social Scraper**: Add actual social media scraping logic
2. **Add Tests**: Unit tests for scrapers and repository
3. **Add Alerts**: Email/Slack notifications on failures
4. **Optimize Queries**: Add database indexes for performance
5. **Add API**: REST API for querying scraped data
6. **Add Dashboard**: Grafana for metrics visualization

## 📄 License

[Your License Here]

## 🤝 Contributing

[Contributing Guidelines]
