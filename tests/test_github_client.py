"""Tests for GitHub Client Manager"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from github import RateLimitExceededException

from src.utils.github_client import GitHubClientManager


class TestGitHubClientManager:
    """Test GitHub client manager functionality"""
    
    @patch('src.utils.github_client.settings')
    @patch('src.utils.github_client.Github')
    def test_initialization(self, mock_github_class, mock_settings):
        """Test client initialization with tokens"""
        # Setup
        mock_settings.github.TOKENS = ['token1', 'token2', 'token3']
        
        # Execute
        manager = GitHubClientManager()
        
        # Assert
        assert manager.tokens == ['token1', 'token2', 'token3']
        assert manager.current_token_index == 0
        assert mock_github_class.called
    
    @patch('src.utils.github_client.settings')
    @patch('src.utils.github_client.Github')
    def test_token_rotation(self, mock_github_class, mock_settings):
        """Test token rotation"""
        # Setup
        mock_settings.github.TOKENS = ['token1', 'token2', 'token3']
        manager = GitHubClientManager()
        
        # Execute - rotate twice
        manager.rotate_token()
        assert manager.current_token_index == 1
        
        manager.rotate_token()
        assert manager.current_token_index == 2
        
        # Should wrap around
        manager.rotate_token()
        assert manager.current_token_index == 0
    
    @patch('src.utils.github_client.settings')
    @patch('src.utils.github_client.Github')
    @patch('src.utils.github_client.time.sleep')
    def test_handle_rate_limit(self, mock_sleep, mock_github_class, mock_settings):
        """Test rate limit handling"""
        # Setup
        mock_settings.github.TOKENS = ['token1', 'token2']
        mock_settings.scraper.TOKEN_ROTATION_DELAY = 60
        manager = GitHubClientManager()
        
        initial_index = manager.current_token_index
        
        # Execute
        manager.handle_rate_limit()
        
        # Assert - should rotate token and sleep
        assert manager.current_token_index != initial_index
        mock_sleep.assert_called_once_with(60)
    
    @patch('src.utils.github_client.settings')
    @patch('src.utils.github_client.Github')
    def test_get_client(self, mock_github_class, mock_settings):
        """Test getting current client"""
        # Setup
        mock_settings.github.TOKENS = ['token1']
        manager = GitHubClientManager()
        
        # Execute
        client = manager.get_client()
        
        # Assert
        assert client is not None
        assert client == manager.github
    
    @patch('src.utils.github_client.settings')
    @patch('src.utils.github_client.Github')
    def test_get_rate_limit_info(self, mock_github_class, mock_settings):
        """Test getting rate limit info"""
        # Setup
        mock_settings.github.TOKENS = ['token1']
        manager = GitHubClientManager()
        
        # Mock rate limit
        mock_rate_limit = Mock()
        mock_rate_limit.core = Mock(remaining=4500, limit=5000)
        mock_rate_limit.search = Mock(remaining=25, limit=30)
        manager.github.get_rate_limit.return_value = mock_rate_limit
        
        # Execute
        info = manager.get_rate_limit_info()
        
        # Assert
        assert 'core' in info
        assert 'search' in info
        assert info['core']['remaining'] == 4500
        assert info['search']['remaining'] == 25
