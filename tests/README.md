# GitHub Scraper - Test Suite

## 🧪 Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# GitHub-related tests
pytest -m github

# Database tests
pytest -m database

# Integration tests
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Test GitHub client
pytest tests/test_github_client.py

# Test username scraper
pytest tests/test_username_scraper.py

# Test profile scraper
pytest tests/test_profile_scraper.py

# Test database repository
pytest tests/test_database_repository.py
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Run Verbose

```bash
pytest -v
```

### Run Specific Test

```bash
pytest tests/test_profile_scraper.py::TestProfileScraper::test_fetch_profile_success -v
```

## 📊 Test Structure

```
tests/
├── conftest.py                    # Fixtures and configuration
├── test_github_client.py          # GitHub client manager tests
├── test_username_scraper.py       # Username scraper tests
├── test_profile_scraper.py        # Profile scraper tests
├── test_database_repository.py    # Database repository tests
├── test_metrics.py                # Metrics collector tests
└── test_integration.py            # Integration tests
```

## ✅ What's Tested

### GitHub Client Manager
- ✅ Token initialization
- ✅ Token rotation
- ✅ Rate limit handling
- ✅ Rate limit info retrieval

### Username Scraper
- ✅ Initialization
- ✅ User search with pagination
- ✅ Rate limit handling and retry
- ✅ Batch username insertion
- ✅ Target limit enforcement

### Profile Scraper
- ✅ Initialization with instance ID
- ✅ Social link extraction (Twitter, LinkedIn, Telegram, etc.)
- ✅ Profile fetching with retry logic
- ✅ Rate limit handling
- ✅ Parallel execution with claiming
- ✅ Error handling and retry count
- ✅ Max retries exceeded handling

### Database Repository
- ✅ Connection with retry
- ✅ Batch username insertion
- ✅ Status-based queries
- ✅ Claim batch for parallel processing (row-level locking)
- ✅ Profile updates
- ✅ Mark as failed
- ✅ Retry count increment
- ✅ Statistics retrieval
- ✅ Datetime parsing

### Metrics Collector
- ✅ Singleton pattern
- ✅ Counter increments
- ✅ Success rate calculation
- ✅ Processing rate calculation
- ✅ Reset functionality

### Integration Tests
- ✅ Complete username scraper flow
- ✅ Complete profile scraper flow
- ✅ Parallel instance coordination

## 🎯 Coverage Goals

- **Target:** 70% minimum
- **Current:** Run `pytest --cov` to check

## 🔧 Writing New Tests

### Example Test

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.github
def test_my_feature(mock_github_user):
    """Test description"""
    # Setup
    ...
    
    # Execute
    result = my_function()
    
    # Assert
    assert result is not None
```

### Using Fixtures

```python
def test_with_fixtures(mock_github_client, mock_database_repository):
    """Use pre-configured mocks"""
    # Fixtures are automatically injected
    assert mock_github_client is not None
```

## 🐛 Debugging Tests

```bash
# Run with print statements visible
pytest -s

# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l
```

## 📝 Test Markers

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.github` - GitHub API related tests
- `@pytest.mark.database` - Database related tests

## 🚀 Continuous Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pip install -r requirements.txt
    pip install -r requirements-test.txt
    pytest --cov=src --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## 📚 Best Practices

1. **Mock external dependencies** - GitHub API, database
2. **Test edge cases** - Empty results, rate limits, errors
3. **Use descriptive test names** - Clear what's being tested
4. **One assertion per test** - Or related assertions
5. **Setup/Execute/Assert** - Clear test structure
6. **Use fixtures** - Reuse common setup code
7. **Test error paths** - Not just happy paths
