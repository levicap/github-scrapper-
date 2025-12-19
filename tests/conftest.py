"""Test configuration and fixtures"""
import pytest
import os
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime

# Set test environment
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'test_github_developers'
os.environ['DB_USER'] = 'test_user'
os.environ['DB_PASSWORD'] = 'test_pass'
os.environ['GITHUB_TOKEN'] = 'test_token_12345'

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent / 'fixtures'


@pytest.fixture
def load_fixture():
    """Helper to load JSON fixtures"""
    def _load(filename):
        fixture_path = FIXTURES_DIR / filename
        with open(fixture_path, 'r') as f:
            return json.load(f)
    return _load


@pytest.fixture
def real_user_profile_data(load_fixture):
    """Load real user profile data from GitHub API"""
    return load_fixture('user_profile_response.json')


@pytest.fixture
def real_search_results(load_fixture):
    """Load real search results from GitHub API"""
    return load_fixture('search_users_response.json')


@pytest.fixture
def mock_github_user(real_user_profile_data):
    """Mock GitHub user object based on real API data"""
    data = real_user_profile_data
    user = Mock()
    user.login = data['login']
    user.name = data['name']
    user.email = data['email']
    user.bio = data['bio']
    user.location = data['location']
    user.company = data['company']
    user.blog = data['blog']
    user.twitter_username = data['twitter_username']
    user.hireable = data['hireable']
    user.followers = data['followers']
    user.following = data['following']
    user.public_repos = data['public_repos']
    user.public_gists = data['public_gists']
    user.created_at = datetime.fromisoformat(data['created_at'].replace('+00:00', ''))
    user.updated_at = datetime.fromisoformat(data['updated_at'].replace('+00:00', ''))
    user.html_url = data['html_url']
    user.avatar_url = data['avatar_url']
    user.type = data['type']
    return user


@pytest.fixture
def mock_github_repo(real_user_profile_data):
    """Mock GitHub repository object based on real API data"""
    data = real_user_profile_data['repositories'][0]  # First repo
    repo = Mock()
    repo.name = data['name']
    repo.full_name = data['full_name']
    repo.stargazers_count = data['stargazers_count']
    repo.language = data['language']
    repo.html_url = data['html_url']
    repo.description = data['description']
    repo.forks_count = data['forks_count']
    repo.watchers_count = data['watchers_count']
    repo.created_at = datetime.fromisoformat(data['created_at'].replace('+00:00', ''))
    repo.updated_at = datetime.fromisoformat(data['updated_at'].replace('+00:00', ''))
    return repo


@pytest.fixture
def mock_github_client(mock_github_user, mock_github_repo):
    """Mock GitHub client"""
    client = Mock()
    
    # Mock search_users
    search_result = Mock()
    search_result.__iter__ = Mock(return_value=iter([mock_github_user]))
    client.search_users.return_value = search_result
    
    # Mock get_user
    client.get_user.return_value = mock_github_user
    
    # Mock repos
    mock_github_user.get_repos.return_value = [mock_github_repo]
    
    # Mock rate limit
    rate_limit = Mock()
    rate_limit.core = Mock(remaining=5000, limit=5000, reset=datetime(2025, 1, 1))
    rate_limit.search = Mock(remaining=30, limit=30, reset=datetime(2025, 1, 1))
    client.get_rate_limit.return_value = rate_limit
    
    return client


@pytest.fixture
def mock_db_connection():
    """Mock database connection"""
    conn = Mock()
    cursor = Mock()
    
    # Mock cursor methods
    cursor.execute = Mock()
    cursor.fetchone = Mock(return_value=(1,))
    cursor.fetchall = Mock(return_value=[])
    cursor.rowcount = 1
    cursor.close = Mock()
    
    # Mock connection methods
    conn.cursor.return_value = cursor
    conn.commit = Mock()
    conn.rollback = Mock()
    conn.close = Mock()
    
    return conn, cursor


@pytest.fixture
def mock_database_repository(mock_db_connection):
    """Mock DatabaseRepository"""
    from src.database import DatabaseRepository
    
    repo = DatabaseRepository()
    repo.conn, repo.cursor = mock_db_connection
    return repo


@pytest.fixture
def sample_profile_data(real_user_profile_data):
    """Sample profile data based on real GitHub API response"""
    data = real_user_profile_data
    return {
        'username': data['login'],
        'name': data['name'],
        'email': data['email'],
        'bio': data['bio'],
        'location': data['location'],
        'company': data['company'],
        'blog': data['blog'],
        'twitter_username': data['twitter_username'],
        'hireable': data['hireable'],
        'followers': data['followers'],
        'following': data['following'],
        'public_repos': data['public_repos'],
        'public_gists': data['public_gists'],
        'created_at': data['created_at'],
        'updated_at': data['updated_at'],
        'profile_url': data['html_url'],
        'avatar_url': data['avatar_url'],
        'social_links': {
            'twitter': f"https://twitter.com/{data['twitter_username']}" if data['twitter_username'] else None,
            'linkedin': None,
            'facebook': None,
            'instagram': None,
            'telegram': None,
            'youtube': None,
            'medium': None,
            'dev_to': None,
            'hashnode': None,
            'stackoverflow': None,
            'other_links': []
        },
        'top_repos': [
            {
                'name': repo['name'],
                'stars': repo['stargazers_count'],
                'language': repo['language'],
                'url': repo['html_url'],
                'description': repo['description']
            }
            for repo in data['repositories'][:5]  # Top 5 repos
        ]
    }


@pytest.fixture
def sample_usernames(real_search_results):
    """Sample usernames list from real GitHub search"""
    return [user['login'] for user in real_search_results['users']]


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics before each test"""
    from src.utils.metrics import metrics
    metrics.reset()
    yield
    metrics.reset()
