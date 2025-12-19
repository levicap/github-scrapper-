"""Tests for Profile Scraper"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from github import RateLimitExceededException

from src.scrapers.profile_scraper import ProfileScraper
from src.database import EnrichmentStatus


@pytest.mark.github
class TestProfileScraper:
    """Test profile scraper functionality"""
    
    @patch('src.scrapers.profile_scraper.DatabaseRepository')
    @patch('src.scrapers.profile_scraper.GitHubClientManager')
    @patch('src.scrapers.profile_scraper.settings')
    def test_initialization(self, mock_settings, mock_gh_client, mock_db):
        """Test scraper initialization with instance ID"""
        # Execute
        scraper = ProfileScraper()
        
        # Assert
        assert scraper.github_client is not None
        assert scraper.db is not None
        assert scraper.scraper_name == 'profile_scraper'
        assert scraper.instance_id is not None
        assert '-' in scraper.instance_id  # Should be hostname-pid format
    
    def test_extract_social_links_twitter(self, mock_github_user, real_user_profile_data):
        """Test extraction of Twitter/X links"""
        # Setup
        with patch('src.scrapers.profile_scraper.DatabaseRepository'), \
             patch('src.scrapers.profile_scraper.GitHubClientManager'), \
             patch('src.scrapers.profile_scraper.settings'):
            scraper = ProfileScraper()
        
        # Execute
        links = scraper._extract_social_links(mock_github_user)
        
        # Assert - use real data from fixture
        expected_twitter = f"https://twitter.com/{real_user_profile_data['twitter_username']}"
        assert links['twitter'] == expected_twitter
    
    def test_extract_social_links_from_bio(self):
        """Test extraction of social links from bio"""
        # Setup
        with patch('src.scrapers.profile_scraper.DatabaseRepository'), \
             patch('src.scrapers.profile_scraper.GitHubClientManager'), \
             patch('src.scrapers.profile_scraper.settings'):
            scraper = ProfileScraper()
        
        mock_user = Mock()
        mock_user.bio = 'Follow me on LinkedIn: linkedin.com/in/johndoe and Telegram: t.me/johndoe'
        mock_user.blog = None
        mock_user.twitter_username = None
        
        # Execute
        links = scraper._extract_social_links(mock_user)
        
        # Assert
        assert links['linkedin'] == 'https://linkedin.com/in/johndoe'
        assert links['telegram'] == 'https://t.me/johndoe'
    
    def test_extract_social_links_other_urls(self):
        """Test extraction of other URLs"""
        # Setup
        with patch('src.scrapers.profile_scraper.DatabaseRepository'), \
             patch('src.scrapers.profile_scraper.GitHubClientManager'), \
             patch('src.scrapers.profile_scraper.settings'):
            scraper = ProfileScraper()
        
        mock_user = Mock()
        mock_user.bio = 'Check my blog: https://myblog.com'
        mock_user.blog = 'https://mywebsite.dev'
        mock_user.twitter_username = None
        
        # Execute
        links = scraper._extract_social_links(mock_user)
        
        # Assert
        assert 'https://myblog.com' in links['other_links']
        assert 'https://mywebsite.dev' in links['other_links']
    
    @patch('src.scrapers.profile_scraper.DatabaseRepository')
    @patch('src.scrapers.profile_scraper.GitHubClientManager')
    @patch('src.scrapers.profile_scraper.settings')
    def test_fetch_profile_success(self, mock_settings, mock_gh_client, mock_db, 
                                   mock_github_user, mock_github_repo):
        """Test successful profile fetching"""
        # Setup
        mock_settings.scraper.MAX_RETRIES = 3
        scraper = ProfileScraper()
        
        # Mock GitHub client
        mock_github = Mock()
        mock_github.get_user.return_value = mock_github_user
        mock_github_user.get_repos.return_value = [mock_github_repo]
        scraper.github_client.get_client = Mock(return_value=mock_github)
        
        # Execute
        profile = scraper.fetch_profile(mock_github_user.login)
        
        # Assert
        assert profile is not None
        assert profile['username'] == mock_github_user.login
        assert profile['name'] == mock_github_user.name
        assert profile['email'] == mock_github_user.email
        assert 'social_links' in profile
        assert 'top_repos' in profile
        assert len(profile['top_repos']) == 1
        assert profile['top_repos'][0]['name'] == 'test-repo'
    
    @patch('src.scrapers.profile_scraper.DatabaseRepository')
    @patch('src.scrapers.profile_scraper.GitHubClientManager')
    @patch('src.scrapers.profile_scraper.settings')
    @patch('src.scrapers.profile_scraper.time.sleep')
    @patch('src.scrapers.profile_scraper.metrics')
    def test_fetch_profile_rate_limit_retry(self, mock_metrics, mock_sleep, 
                                            mock_settings, mock_gh_client, mock_db,
                                            mock_github_user):
        """Test profile fetch with rate limit and retry"""
        # Setup
        mock_settings.scraper.MAX_RETRIES = 3
        mock_settings.scraper.RETRY_DELAY = 1
        mock_settings.scraper.EXPONENTIAL_BACKOFF = True
        
        scraper = ProfileScraper()
        scraper.db.mark_as_failed = Mock()
        
        # Mock GitHub to fail once with rate limit, then succeed
        mock_github = Mock()
        mock_github.get_user.side_effect = [
            RateLimitExceededException(403, 'Rate limit', None),
            mock_github_user
        ]
        mock_github_user.get_repos.return_value = []
        
        scraper.github_client.get_client = Mock(return_value=mock_github)
        scraper.github_client.handle_rate_limit = Mock()
        
        # Execute
        profile = scraper.fetch_profile('test_user')
        
        # Assert
        assert profile is not None
        assert scraper.github_client.handle_rate_limit.called
        assert mock_metrics.increment.called
    
    @patch('src.scrapers.profile_scraper.DatabaseRepository')
    @patch('src.scrapers.profile_scraper.GitHubClientManager')
    @patch('src.scrapers.profile_scraper.settings')
    @patch('src.scrapers.profile_scraper.time.sleep')
    def test_fetch_profile_max_retries_exceeded(self, mock_sleep, mock_settings, 
                                                 mock_gh_client, mock_db):
        """Test profile fetch failure after max retries"""
        # Setup
        mock_settings.scraper.MAX_RETRIES = 2
        mock_settings.scraper.RETRY_DELAY = 1
        mock_settings.scraper.EXPONENTIAL_BACKOFF = False
        
        scraper = ProfileScraper()
        scraper.db.mark_as_failed = Mock()
        
        # Mock GitHub to always fail
        mock_github = Mock()
        mock_github.get_user.side_effect = Exception('API Error')
        scraper.github_client.get_client = Mock(return_value=mock_github)
        
        # Execute
        profile = scraper.fetch_profile('test_user')
        
        # Assert
        assert profile is None
        assert scraper.db.mark_as_failed.called
    
    @patch('src.scrapers.profile_scraper.DatabaseRepository')
    @patch('src.scrapers.profile_scraper.GitHubClientManager')
    @patch('src.scrapers.profile_scraper.settings')
    @patch('src.scrapers.profile_scraper.time.sleep')
    @patch('src.scrapers.profile_scraper.metrics')
    def test_scrape_profiles_with_claiming(self, mock_metrics, mock_sleep, 
                                          mock_settings, mock_gh_client, mock_db,
                                          mock_github_user):
        """Test parallel-safe profile scraping with claiming"""
        # Setup
        mock_settings.scraper.TARGET_PROFILES = 100
        mock_settings.scraper.RATE_LIMIT_DELAY = 1
        
        scraper = ProfileScraper()
        
        # Mock database operations
        scraper.db.get_username_count_by_status = Mock(side_effect=[50, 53, 56, 100])
        scraper.db.claim_batch_for_processing = Mock(side_effect=[
            ['user1', 'user2', 'user3'],  # First batch
            []  # No more records
        ])
        scraper.db.update_profile = Mock(return_value=1)
        
        # Mock GitHub
        mock_github = Mock()
        mock_github.get_user.return_value = mock_github_user
        mock_github_user.get_repos.return_value = []
        scraper.github_client.get_client = Mock(return_value=mock_github)
        
        # Execute
        scraper.scrape_profiles()
        
        # Assert
        assert scraper.db.claim_batch_for_processing.called
        assert scraper.db.update_profile.call_count == 3  # 3 users processed
        assert mock_github.get_user.call_count == 3
    
    @patch('src.scrapers.profile_scraper.DatabaseRepository')
    @patch('src.scrapers.profile_scraper.GitHubClientManager')
    @patch('src.scrapers.profile_scraper.settings')
    def test_scrape_profiles_target_reached(self, mock_settings, mock_gh_client, mock_db):
        """Test scraping stops when target is reached"""
        # Setup
        mock_settings.scraper.TARGET_PROFILES = 100
        
        scraper = ProfileScraper()
        scraper.db.get_username_count_by_status = Mock(return_value=150)  # Already exceeded
        
        # Execute
        scraper.scrape_profiles()
        
        # Assert - should exit early without claiming
        assert not scraper.db.claim_batch_for_processing.called
    
    @patch('src.scrapers.profile_scraper.DatabaseRepository')
    @patch('src.scrapers.profile_scraper.GitHubClientManager')
    @patch('src.scrapers.profile_scraper.settings')
    @patch('src.scrapers.profile_scraper.time.sleep')
    def test_scrape_profiles_error_handling(self, mock_sleep, mock_settings, 
                                           mock_gh_client, mock_db):
        """Test error handling during profile scraping"""
        # Setup
        mock_settings.scraper.TARGET_PROFILES = 100
        mock_settings.scraper.RATE_LIMIT_DELAY = 1
        
        scraper = ProfileScraper()
        scraper.db.get_username_count_by_status = Mock(side_effect=[50, 50, 100])
        scraper.db.claim_batch_for_processing = Mock(side_effect=[
            ['user_error'],
            []
        ])
        scraper.db.increment_retry_count = Mock(return_value=1)
        
        # Mock fetch_profile to raise exception
        scraper.fetch_profile = Mock(side_effect=Exception('Network error'))
        
        # Execute
        scraper.scrape_profiles()
        
        # Assert - should handle error and increment retry count
        assert scraper.db.increment_retry_count.called
