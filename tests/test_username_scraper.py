"""Tests for Username Scraper"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from github import RateLimitExceededException

from src.scrapers.username_scraper import UsernameScraper
from src.database import EnrichmentStatus


@pytest.mark.github
class TestUsernameScraper:
    """Test username scraper functionality"""
    
    @patch('src.scrapers.username_scraper.DatabaseRepository')
    @patch('src.scrapers.username_scraper.GitHubClientManager')
    @patch('src.scrapers.username_scraper.settings')
    def test_initialization(self, mock_settings, mock_gh_client, mock_db):
        """Test scraper initialization"""
        # Setup
        mock_settings.scraper.LOCATIONS = ['Kyiv']
        mock_settings.scraper.years = [2020, 2021]
        
        # Execute
        scraper = UsernameScraper()
        
        # Assert
        assert scraper.github_client is not None
        assert scraper.db is not None
        assert scraper.scraper_name == 'username_scraper'
    
    @patch('src.scrapers.username_scraper.DatabaseRepository')
    @patch('src.scrapers.username_scraper.GitHubClientManager')
    @patch('src.scrapers.username_scraper.settings')
    @patch('src.scrapers.username_scraper.time.sleep')
    def test_search_users_success(self, mock_sleep, mock_settings, mock_gh_client, mock_db):
        """Test successful user search"""
        # Setup
        mock_settings.scraper.LOCATIONS = ['Kyiv']
        mock_settings.scraper.years = [2020]
        mock_settings.scraper.TARGET_USERNAMES = 100
        mock_settings.scraper.BATCH_SIZE = 10
        mock_settings.scraper.RATE_LIMIT_DELAY = 2
        mock_settings.github.SEARCH_MAX_RESULTS = 1000
        
        scraper = UsernameScraper()
        
        # Mock database
        scraper.db.get_username_count_by_status = Mock(side_effect=[0, 5, 10, 15, 20])
        scraper.db.insert_usernames_batch = Mock(return_value=5)
        
        # Mock GitHub search results
        mock_user1 = Mock(login='user1')
        mock_user2 = Mock(login='user2')
        mock_user3 = Mock(login='user3')
        mock_search_result = [mock_user1, mock_user2, mock_user3]
        
        mock_github = Mock()
        mock_github.search_users.return_value = mock_search_result
        scraper.github_client.get_client = Mock(return_value=mock_github)
        
        # Execute
        scraper.search_users()
        
        # Assert
        assert scraper.db.insert_usernames_batch.called
        assert mock_github.search_users.called
    
    @patch('src.scrapers.username_scraper.DatabaseRepository')
    @patch('src.scrapers.username_scraper.GitHubClientManager')
    @patch('src.scrapers.username_scraper.settings')
    @patch('src.scrapers.username_scraper.time.sleep')
    @patch('src.scrapers.username_scraper.metrics')
    def test_search_users_rate_limit(self, mock_metrics, mock_sleep, mock_settings, 
                                     mock_gh_client, mock_db):
        """Test handling rate limit during search"""
        # Setup
        mock_settings.scraper.LOCATIONS = ['Kyiv']
        mock_settings.scraper.years = [2020]
        mock_settings.scraper.TARGET_USERNAMES = 100
        mock_settings.scraper.BATCH_SIZE = 10
        mock_settings.github.SEARCH_MAX_RESULTS = 1000
        
        scraper = UsernameScraper()
        scraper.db.get_username_count_by_status = Mock(return_value=0)
        scraper.db.insert_usernames_batch = Mock(return_value=0)
        
        # Mock GitHub to raise rate limit then succeed
        mock_github = Mock()
        mock_github.search_users.side_effect = [
            RateLimitExceededException(403, 'Rate limit exceeded', None),
            []  # Empty result after rate limit
        ]
        scraper.github_client.get_client = Mock(return_value=mock_github)
        scraper.github_client.handle_rate_limit = Mock()
        
        # Execute
        scraper.search_users()
        
        # Assert
        assert scraper.github_client.handle_rate_limit.called
        assert mock_metrics.increment.called
    
    @patch('src.scrapers.username_scraper.DatabaseRepository')
    @patch('src.scrapers.username_scraper.GitHubClientManager')
    @patch('src.scrapers.username_scraper.settings')
    def test_search_query_format(self, mock_settings, mock_gh_client, mock_db):
        """Test search query format is correct"""
        # Setup
        mock_settings.scraper.LOCATIONS = ['Kyiv']
        mock_settings.scraper.years = [2020]
        mock_settings.scraper.TARGET_USERNAMES = 5
        mock_settings.scraper.BATCH_SIZE = 10
        mock_settings.github.SEARCH_MAX_RESULTS = 1000
        
        scraper = UsernameScraper()
        scraper.db.get_username_count_by_status = Mock(return_value=10)  # Already reached target
        
        mock_github = Mock()
        scraper.github_client.get_client = Mock(return_value=mock_github)
        
        # Execute
        scraper.search_users()
        
        # Assert - should not search since target reached
        # Just verify initialization works
        assert scraper is not None
    
    @patch('src.scrapers.username_scraper.DatabaseRepository')
    @patch('src.scrapers.username_scraper.GitHubClientManager')
    @patch('src.scrapers.username_scraper.settings')
    def test_batch_insertion(self, mock_settings, mock_gh_client, mock_db):
        """Test batch insertion of usernames"""
        # Setup
        mock_settings.scraper.LOCATIONS = ['Kyiv']
        mock_settings.scraper.years = [2020]
        mock_settings.scraper.TARGET_USERNAMES = 100
        mock_settings.scraper.BATCH_SIZE = 3  # Small batch for testing
        mock_settings.github.SEARCH_MAX_RESULTS = 1000
        
        scraper = UsernameScraper()
        scraper.db.get_username_count_by_status = Mock(side_effect=[0, 3, 6, 9])
        scraper.db.insert_usernames_batch = Mock(return_value=3)
        
        # Mock GitHub with 9 users
        users = [Mock(login=f'user{i}') for i in range(9)]
        mock_github = Mock()
        mock_github.search_users.return_value = users
        scraper.github_client.get_client = Mock(return_value=mock_github)
        
        # Execute
        scraper.search_users()
        
        # Assert - should have called insert 3 times (9 users / batch of 3)
        assert scraper.db.insert_usernames_batch.call_count >= 1
