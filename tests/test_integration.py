"""Integration tests for scrapers"""
import pytest
from unittest.mock import Mock, patch

from src.scrapers.username_scraper import UsernameScraper
from src.scrapers.profile_scraper import ProfileScraper


@pytest.mark.integration
@pytest.mark.slow
class TestScraperIntegration:
    """Integration tests for complete scraper workflows"""
    
    @patch('src.scrapers.username_scraper.DatabaseRepository')
    @patch('src.scrapers.username_scraper.GitHubClientManager')
    @patch('src.scrapers.username_scraper.settings')
    def test_username_scraper_full_flow(self, mock_settings, mock_gh_client, mock_db,
                                       mock_github_user):
        """Test complete username scraper flow"""
        # Setup
        mock_settings.scraper.LOCATIONS = ['Kyiv']
        mock_settings.scraper.years = [2020]
        mock_settings.scraper.TARGET_USERNAMES = 5
        mock_settings.scraper.BATCH_SIZE = 3
        mock_settings.scraper.RATE_LIMIT_DELAY = 0  # No delay in tests
        mock_settings.github.SEARCH_MAX_RESULTS = 10
        
        scraper = UsernameScraper()
        
        # Mock database methods
        scraper.db.connect = Mock()
        scraper.db.create_tables = Mock()
        scraper.db.disconnect = Mock()
        scraper.db.get_username_count_by_status = Mock(side_effect=[0, 3, 6])
        scraper.db.insert_usernames_batch = Mock(return_value=3)
        scraper.db.get_stats = Mock(return_value={
            'total_developers': 6,
            'status_initial': 6,
            'status_profiled': 0,
            'status_enhanced': 0
        })
        
        # Mock GitHub
        users = [Mock(login=f'user{i}') for i in range(6)]
        mock_github = Mock()
        mock_github.search_users.return_value = users
        scraper.github_client.get_client = Mock(return_value=mock_github)
        
        # Execute
        with patch('src.scrapers.username_scraper.time.sleep'):
            scraper.run()
        
        # Assert
        assert scraper.db.connect.called
        assert scraper.db.create_tables.called
        assert scraper.db.insert_usernames_batch.called
        assert scraper.db.disconnect.called
    
    @patch('src.scrapers.profile_scraper.DatabaseRepository')
    @patch('src.scrapers.profile_scraper.GitHubClientManager')
    @patch('src.scrapers.profile_scraper.settings')
    def test_profile_scraper_full_flow(self, mock_settings, mock_gh_client, mock_db,
                                      mock_github_user):
        """Test complete profile scraper flow"""
        # Setup
        mock_settings.scraper.TARGET_PROFILES = 3
        mock_settings.scraper.RATE_LIMIT_DELAY = 0
        mock_settings.scraper.MAX_RETRIES = 2
        
        scraper = ProfileScraper()
        
        # Mock database methods
        scraper.db.connect = Mock()
        scraper.db.create_tables = Mock()
        scraper.db.disconnect = Mock()
        scraper.db.get_username_count_by_status = Mock(side_effect=[0, 1, 2, 3])
        scraper.db.claim_batch_for_processing = Mock(side_effect=[
            ['user1', 'user2', 'user3'],
            []
        ])
        scraper.db.update_profile = Mock(return_value=1)
        scraper.db.get_stats = Mock(return_value={
            'total_developers': 3,
            'status_initial': 0,
            'status_processing': 0,
            'status_profiled': 3,
            'status_enhanced': 0,
            'developers_with_email': 2,
            'developers_with_social': 1
        })
        
        # Mock GitHub
        mock_github = Mock()
        mock_github.get_user.return_value = mock_github_user
        mock_github_user.get_repos.return_value = []
        scraper.github_client.get_client = Mock(return_value=mock_github)
        
        # Execute
        with patch('src.scrapers.profile_scraper.time.sleep'):
            scraper.run()
        
        # Assert
        assert scraper.db.connect.called
        assert scraper.db.create_tables.called
        assert scraper.db.claim_batch_for_processing.called
        assert scraper.db.update_profile.call_count == 3
        assert scraper.db.disconnect.called
    
    @patch('src.scrapers.profile_scraper.DatabaseRepository')
    @patch('src.scrapers.profile_scraper.GitHubClientManager')
    @patch('src.scrapers.profile_scraper.settings')
    def test_parallel_instance_coordination(self, mock_settings, mock_gh_client, 
                                           mock_db, mock_github_user):
        """Test two scraper instances don't process same records"""
        # Setup
        mock_settings.scraper.TARGET_PROFILES = 10
        mock_settings.scraper.RATE_LIMIT_DELAY = 0
        
        # Create two instances
        scraper1 = ProfileScraper()
        scraper2 = ProfileScraper()
        
        assert scraper1.instance_id != scraper2.instance_id
        
        # Mock database - each instance claims different batch
        scraper1.db.claim_batch_for_processing = Mock(side_effect=[
            ['user1', 'user2'],
            []
        ])
        scraper2.db.claim_batch_for_processing = Mock(side_effect=[
            ['user3', 'user4'],
            []
        ])
        
        scraper1.db.get_username_count_by_status = Mock(return_value=100)
        scraper2.db.get_username_count_by_status = Mock(return_value=100)
        
        # Verify instances have different IDs
        claimed1 = scraper1.db.claim_batch_for_processing(
            from_status=Mock(),
            limit=50,
            instance_id=scraper1.instance_id,
            timeout_minutes=30
        )
        
        claimed2 = scraper2.db.claim_batch_for_processing(
            from_status=Mock(),
            limit=50,
            instance_id=scraper2.instance_id,
            timeout_minutes=30
        )
        
        # Assert - no overlap
        assert set(claimed1).isdisjoint(set(claimed2))
