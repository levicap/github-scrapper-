# Test Fixtures - Real GitHub API Responses

This directory contains real GitHub API responses captured for testing purposes. These fixtures ensure our tests match actual API behavior.

## Files

### `search_users_response.json`
Real GitHub user search results for the query: `location:Kyiv created:2020-01-01..2020-12-31`

**Contains:**
- 5 real GitHub users from Kyiv
- User logins, IDs, profile URLs
- Mix of User and Organization types

**Usage:** Testing username scraper functionality

### `user_profile_response.json`
Complete profile data for a real GitHub user (`lgtome`)

**Contains:**
- Full profile information (name, bio, location, company, etc.)
- Social media links (Twitter: `lgtomee`)
- Repository list (10 repos with stats)
- Followers/following counts
- Account timestamps

**Usage:** Testing profile scraper and data extraction

### `multiple_users_response.json`
Batch of 3 user profiles from Ukraine with >10 followers

**Contains:**
- `mourner` - Popular developer
- `NARKOZ` - Active contributor  
- `tshemsedinov` - Well-known in community

**Usage:** Testing batch operations and multiple user processing

### `rate_limit_response.json`
GitHub API rate limit information

**Contains:**
- Core API limits (remaining/total)
- Search API limits
- Reset timestamps

**Usage:** Testing rate limit handling and token rotation

## Regenerating Fixtures

If you need fresh data (e.g., API changes, expired data):

```bash
python scripts/fetch_test_fixtures.py
```

**Requirements:**
- Valid `GITHUB_TOKEN` in `.env` file
- Internet connection
- Available API rate limit

## Notes

- **Real Data:** These are actual GitHub profiles and data
- **Privacy:** Only public information is captured
- **Timestamps:** Some timestamps may become outdated but structure remains valid
- **Rate Limits:** Reflected limits are from the time of capture

## Why Real Fixtures?

1. **Accuracy:** Tests match actual API responses
2. **Edge Cases:** Captures real-world data variations (nulls, special chars, etc.)
3. **Confidence:** If tests pass with real data, production will work
4. **Documentation:** Shows developers what actual API responses look like

## Example Usage in Tests

```python
def test_with_real_data(load_fixture):
    """Test using real GitHub API response"""
    profile = load_fixture('user_profile_response.json')
    assert profile['login'] == 'lgtome'
    assert profile['location'] == 'Ukraine, Kyiv'
```
