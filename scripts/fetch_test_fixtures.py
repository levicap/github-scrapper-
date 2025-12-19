"""
Fetch real GitHub API responses to use as test fixtures
Run this script to generate sample data for tests
"""
import json
import os
from pathlib import Path
from github import Github
from dotenv import load_dotenv

load_dotenv()

# Create fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / 'tests' / 'fixtures'
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

def fetch_user_search_response():
    """Fetch a sample user search response"""
    print("Fetching user search results...")
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        raise ValueError("GITHUB_TOKEN not found in .env file")
    
    g = Github(github_token)
    
    # Search for users in Kyiv
    query = "location:Kyiv created:2020-01-01..2020-12-31"
    users = g.search_users(query)
    
    # Get first 5 users
    user_list = []
    for i, user in enumerate(users):
        if i >= 5:
            break
        
        user_data = {
            'login': user.login,
            'id': user.id,
            'type': user.type,
            'html_url': user.html_url,
            'avatar_url': user.avatar_url,
        }
        user_list.append(user_data)
        print(f"  - Found user: {user.login}")
    
    # Save to file
    fixture_path = FIXTURES_DIR / 'search_users_response.json'
    with open(fixture_path, 'w') as f:
        json.dump({
            'query': query,
            'total_count': min(len(user_list), 1000),
            'users': user_list
        }, f, indent=2)
    
    print(f"✅ Saved search results to {fixture_path}")
    return user_list[0]['login'] if user_list else None


def fetch_user_profile_response(username=None):
    """Fetch a sample user profile response"""
    print(f"\nFetching user profile...")
    
    github_token = os.getenv('GITHUB_TOKEN')
    g = Github(github_token)
    
    # Use provided username or get a random one
    if not username:
        # Get a user from Ukraine
        users = g.search_users("location:Ukraine")
        username = list(users)[0].login
    
    print(f"  - Getting profile for: {username}")
    user = g.get_user(username)
    
    # Extract all profile data
    profile_data = {
        'login': user.login,
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'bio': user.bio,
        'location': user.location,
        'company': user.company,
        'blog': user.blog,
        'twitter_username': user.twitter_username,
        'hireable': user.hireable,
        'followers': user.followers,
        'following': user.following,
        'public_repos': user.public_repos,
        'public_gists': user.public_gists,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        'html_url': user.html_url,
        'avatar_url': user.avatar_url,
        'type': user.type,
    }
    
    # Get repositories
    repos = []
    for i, repo in enumerate(user.get_repos(sort='updated')):
        if i >= 10:  # Get top 10 repos
            break
        
        repos.append({
            'name': repo.name,
            'full_name': repo.full_name,
            'description': repo.description,
            'html_url': repo.html_url,
            'stargazers_count': repo.stargazers_count,
            'watchers_count': repo.watchers_count,
            'forks_count': repo.forks_count,
            'language': repo.language,
            'created_at': repo.created_at.isoformat() if repo.created_at else None,
            'updated_at': repo.updated_at.isoformat() if repo.updated_at else None,
        })
    
    profile_data['repositories'] = repos
    
    # Save to file
    fixture_path = FIXTURES_DIR / 'user_profile_response.json'
    with open(fixture_path, 'w') as f:
        json.dump(profile_data, f, indent=2)
    
    print(f"✅ Saved profile data to {fixture_path}")
    print(f"   Repos: {len(repos)}, Followers: {user.followers}")


def fetch_rate_limit_response():
    """Fetch rate limit response"""
    print(f"\nFetching rate limit info...")
    
    github_token = os.getenv('GITHUB_TOKEN')
    g = Github(github_token)
    
    rate_limit = g.get_rate_limit()
    
    # Access rate limit properly - it's a named tuple with .core, .search attributes
    rate_limit_data = {
        'core': {
            'limit': rate_limit.core.limit if hasattr(rate_limit, 'core') else 5000,
            'remaining': rate_limit.core.remaining if hasattr(rate_limit, 'core') else 4999,
            'reset': rate_limit.core.reset.isoformat() if hasattr(rate_limit, 'core') else '2025-12-20T00:00:00',
        },
        'search': {
            'limit': rate_limit.search.limit if hasattr(rate_limit, 'search') else 30,
            'remaining': rate_limit.search.remaining if hasattr(rate_limit, 'search') else 29,
            'reset': rate_limit.search.reset.isoformat() if hasattr(rate_limit, 'search') else '2025-12-20T00:00:00',
        }
    }
    
    # Save to file
    fixture_path = FIXTURES_DIR / 'rate_limit_response.json'
    with open(fixture_path, 'w') as f:
        json.dump(rate_limit_data, f, indent=2)
    
    print(f"✅ Saved rate limit data to {fixture_path}")
    if hasattr(rate_limit, 'search'):
        print(f"   Search remaining: {rate_limit.search.remaining}/{rate_limit.search.limit}")


def fetch_multiple_users():
    """Fetch multiple user profiles for testing batch operations"""
    print(f"\nFetching multiple user profiles...")
    
    github_token = os.getenv('GITHUB_TOKEN')
    g = Github(github_token)
    
    # Get 3 users from Ukraine
    users = g.search_users("location:Ukraine followers:>10")
    
    user_profiles = []
    for i, user in enumerate(users):
        if i >= 3:
            break
        
        print(f"  - Fetching: {user.login}")
        profile = {
            'login': user.login,
            'name': user.name,
            'email': user.email,
            'bio': user.bio,
            'location': user.location,
            'company': user.company,
            'blog': user.blog,
            'twitter_username': user.twitter_username,
            'followers': user.followers,
            'public_repos': user.public_repos,
            'html_url': user.html_url,
        }
        user_profiles.append(profile)
    
    # Save to file
    fixture_path = FIXTURES_DIR / 'multiple_users_response.json'
    with open(fixture_path, 'w') as f:
        json.dump(user_profiles, f, indent=2)
    
    print(f"✅ Saved {len(user_profiles)} user profiles to {fixture_path}")


def main():
    """Fetch all test fixtures"""
    print("=" * 70)
    print("Fetching GitHub API Test Fixtures")
    print("=" * 70)
    
    try:
        # Fetch search results and get a username
        first_username = fetch_user_search_response()
        
        # Fetch user profile
        fetch_user_profile_response(first_username)
        
        # Fetch rate limit
        fetch_rate_limit_response()
        
        # Fetch multiple users
        fetch_multiple_users()
        
        print("\n" + "=" * 70)
        print("✅ All fixtures fetched successfully!")
        print(f"📁 Fixtures saved to: {FIXTURES_DIR}")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("1. You have a valid GITHUB_TOKEN in .env file")
        print("2. The token has necessary permissions")
        print("3. You haven't hit rate limits")


if __name__ == '__main__':
    main()
