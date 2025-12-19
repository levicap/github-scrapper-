# Parallel Execution Guide

## 🚀 Running Multiple Scraper Instances

The project now **fully supports running multiple instances of the same scraper concurrently**! This enables horizontal scaling and faster processing.

## ✅ What Changed

### 1. **Row-Level Locking**
- Uses PostgreSQL's `FOR UPDATE SKIP LOCKED` to prevent race conditions
- Each instance "claims" records before processing
- No two instances will process the same username

### 2. **PROCESSING Status**
- New intermediate status: `INITIAL → PROCESSING → PROFILED → ENHANCED`
- Records in `PROCESSING` are actively being worked on
- Stale claims (crashed instances) are automatically released after timeout

### 3. **Instance Identification**
- Each instance has a unique ID: `hostname-pid`
- Claims are tracked with `claimed_by` and `processing_started_at`
- Easy to monitor which instance is processing what

### 4. **Automatic Stale Claim Release**
- If an instance crashes, its claims are released after 30 minutes (configurable)
- Other instances can pick up the work automatically

---

## 📊 Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Instance 1 │     │  Instance 2 │     │  Instance 5 │
│  (Profile)  │     │  (Profile)  │     │  (Profile)  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │    Claim batch    │    Claim batch    │    Claim batch
       │    (50 records)   │    (50 records)   │    (50 records)
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                    ┌──────▼──────┐
                    │  PostgreSQL │
                    │  (RDS/Local)│
                    └─────────────┘
                    Row-level locks
                    prevent conflicts
```

---

## 🏃 How to Run Multiple Instances

### Option 1: Local (Multiple Terminals)

```bash
# Terminal 1
python scripts/run_profile_scraper.py

# Terminal 2
python scripts/run_profile_scraper.py

# Terminal 3
python scripts/run_profile_scraper.py

# Each gets a unique instance ID and claims different records
```

### Option 2: Docker Compose (Scale Up)

```bash
# Run 5 instances of profile scraper
docker compose -f docker/docker-compose.yml up --scale profile_scraper=5

# Run 2 username scrapers and 10 social scrapers
docker compose -f docker/docker-compose.yml up \
  --scale username_scraper=2 \
  --scale social_scraper=10
```

### Option 3: Docker (Manual Containers)

```bash
# Start 5 profile scraper instances
for i in {1..5}; do
  docker run -d \
    --name profile_scraper_$i \
    --env-file .env \
    github-scraper:latest \
    python -m src.scrapers.profile_scraper
done
```

### Option 4: Kubernetes (Production)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: profile-scraper
spec:
  replicas: 5  # Run 5 instances
  selector:
    matchLabels:
      app: profile-scraper
  template:
    metadata:
      labels:
        app: profile-scraper
    spec:
      containers:
      - name: scraper
        image: github-scraper:latest
        command: ["python", "-m", "src.scrapers.profile_scraper"]
        env:
          - name: DB_HOST
            valueFrom:
              secretKeyRef:
                name: db-credentials
                key: host
```

### Option 5: ECS (AWS)

```json
{
  "family": "github-profile-scraper",
  "containerDefinitions": [{
    "name": "scraper",
    "image": "your-ecr-repo/github-scraper:latest",
    "command": ["python", "-m", "src.scrapers.profile_scraper"],
    "environment": [
      {"name": "DB_HOST", "value": "your-rds-endpoint.rds.amazonaws.com"}
    ]
  }],
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512"
}

# Run task with desired count
aws ecs run-task \
  --cluster your-cluster \
  --task-definition github-profile-scraper \
  --count 5 \
  --launch-type FARGATE
```

---

## ⚙️ Configuration

### Batch Size

Edit `src/scrapers/profile_scraper.py`:

```python
batch_size = 50  # Each instance claims 50 records at a time
```

**Recommendations:**
- Small batch (10-20): Better load distribution, more DB queries
- Large batch (100-200): Fewer DB queries, less even distribution
- **Default (50)**: Good balance

### Claim Timeout

Edit the claim timeout in scraper:

```python
claimed_usernames = self.db.claim_batch_for_processing(
    from_status=EnrichmentStatus.INITIAL,
    limit=batch_size,
    instance_id=self.instance_id,
    timeout_minutes=30  # Adjust this
)
```

**Recommendations:**
- Fast processing: 15-30 minutes
- Slow processing (rate-limited): 60-120 minutes
- **Default (30 min)**: Works for most cases

---

## 📊 Monitoring Multiple Instances

### Check Active Claims

```sql
-- See which instances are currently processing
SELECT 
    claimed_by,
    COUNT(*) as records_claimed,
    MIN(processing_started_at) as started,
    MAX(processing_started_at) as last_claim
FROM developers
WHERE enrichment_status = 'PROCESSING'
GROUP BY claimed_by;
```

### Monitor Progress by Instance

```sql
-- See what each instance has completed
SELECT 
    claimed_by,
    COUNT(*) as completed
FROM developers
WHERE enrichment_status = 'PROFILED'
    AND profiled_at > NOW() - INTERVAL '1 hour'
GROUP BY claimed_by
ORDER BY completed DESC;
```

### Find Stale Claims

```sql
-- Find claims that might be stale
SELECT 
    username,
    claimed_by,
    processing_started_at,
    EXTRACT(EPOCH FROM (NOW() - processing_started_at))/60 as minutes_ago
FROM developers
WHERE enrichment_status = 'PROCESSING'
    AND processing_started_at < NOW() - INTERVAL '30 minutes'
ORDER BY processing_started_at;
```

---

## 🎯 Best Practices

### 1. **Start Small, Scale Up**
```bash
# Start with 1 instance
python scripts/run_profile_scraper.py

# Monitor for 5-10 minutes, check for issues
# If stable, add more instances
```

### 2. **Monitor Database Load**
```sql
-- Check for lock contention
SELECT * FROM pg_stat_activity 
WHERE wait_event_type = 'Lock';

-- Check connection count
SELECT COUNT(*) FROM pg_stat_activity;
```

### 3. **Use Connection Pooling**
For high concurrency, consider using PgBouncer:

```bash
# docker-compose.yml
pgbouncer:
  image: edoburu/pgbouncer
  environment:
    DATABASE_URL: postgres://user:pass@postgres:5432/github_developers
    MAX_CLIENT_CONN: 100
    DEFAULT_POOL_SIZE: 25
```

### 4. **Rate Limit Considerations**

With multiple instances, you'll hit rate limits faster. Solutions:

- **Add more GitHub tokens** in `.env`
- **Distribute tokens** across instances
- **Increase delays** in `settings.py`

```python
# src/config/settings.py
RATE_LIMIT_DELAY: int = 5  # Increase if running many instances
```

### 5. **Log Aggregation**

Use centralized logging for multiple instances:

```python
# Example: Send logs to CloudWatch, Datadog, or ELK
import logging
from pythonjsonlogger import jsonlogger

handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter())
```

---

## 🚨 Troubleshooting

### Issue: "No more records to claim"

**Cause:** All records are either PROCESSING or already PROFILED

**Solution:**
```sql
-- Check status distribution
SELECT enrichment_status, COUNT(*) 
FROM developers 
GROUP BY enrichment_status;

-- If many stuck in PROCESSING, manually release:
UPDATE developers
SET enrichment_status = 'INITIAL',
    claimed_by = NULL,
    processing_started_at = NULL
WHERE enrichment_status = 'PROCESSING'
    AND processing_started_at < NOW() - INTERVAL '1 hour';
```

### Issue: High Database CPU

**Cause:** Too many concurrent instances

**Solution:**
- Reduce number of instances
- Increase batch size
- Add database connection pooling
- Scale up database (more CPU/RAM)

### Issue: Uneven Load Distribution

**Cause:** Some instances finishing faster than others

**Solution:**
- Reduce batch size for more even distribution
- Ensure all instances have same configuration
- Check for rate limit hits (some tokens might be exhausted)

---

## 📈 Performance Estimates

### Single Instance
- Processing rate: ~50-100 profiles/hour (with rate limits)

### 5 Instances
- Processing rate: ~250-500 profiles/hour
- **5x faster!** (with enough GitHub tokens)

### 10 Instances
- Processing rate: ~500-800 profiles/hour
- Diminishing returns due to rate limits
- **Recommended: Add more GitHub tokens**

---

## ✅ Quick Start for Parallel Execution

```bash
# 1. Update your database schema
python migrate_database.py

# 2. Run 2 username scrapers, 5 profile scrapers
docker compose -f docker/docker-compose.yml up \
  --scale username_scraper=2 \
  --scale profile_scraper=5

# 3. Monitor progress
docker compose logs -f profile_scraper

# 4. Check database
psql -h localhost -U ahmed -d github_developers \
  -c "SELECT enrichment_status, COUNT(*) FROM developers GROUP BY enrichment_status;"
```

That's it! Your scrapers are now running in parallel and processing much faster! 🚀
