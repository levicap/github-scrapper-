"""Tests for Database Repository"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.database.repository import DatabaseRepository
from src.database.models import EnrichmentStatus


@pytest.mark.database
class TestDatabaseRepository:
    """Test database repository functionality"""
    
    @patch('src.database.repository.psycopg2.connect')
    @patch('src.database.repository.settings')
    def test_connect_success(self, mock_settings, mock_connect):
        """Test successful database connection"""
        # Setup
        mock_db_config = Mock()
        mock_db_config.config_dict = {
            'host': 'localhost',
            'port': '5432',
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass'
        }
        mock_scraper_config = Mock()
        mock_scraper_config.MAX_RETRIES = 3
        
        mock_settings.database = mock_db_config
        mock_settings.scraper = mock_scraper_config
        
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        # Execute
        repo = DatabaseRepository()
        repo.connect()
        
        # Assert
        assert mock_connect.called
        assert repo.conn == mock_conn
    
    @patch('src.database.repository.psycopg2.connect')
    @patch('src.database.repository.settings')
    @patch('src.database.repository.time.sleep')
    def test_connect_retry(self, mock_sleep, mock_settings, mock_connect):
        """Test connection retry on failure"""
        # Setup
        mock_db_config = Mock()
        mock_db_config.config_dict = {'host': 'localhost'}
        mock_scraper_config = Mock()
        mock_scraper_config.MAX_RETRIES = 3
        mock_scraper_config.RETRY_DELAY = 1
        mock_scraper_config.EXPONENTIAL_BACKOFF = True
        
        mock_settings.database = mock_db_config
        mock_settings.scraper = mock_scraper_config
        
        mock_connect.side_effect = [
            Exception('Connection failed'),
            Exception('Connection failed'),
            Mock()  # Success on third try
        ]
        
        # Execute
        repo = DatabaseRepository()
        repo.connect()
        
        # Assert
        assert mock_connect.call_count == 3
        assert mock_sleep.call_count == 2  # Slept between retries
    
    def test_insert_usernames_batch(self, mock_database_repository):
        """Test batch insertion of usernames"""
        # Setup
        repo = mock_database_repository
        usernames = ['user1', 'user2', 'user3']
        
        # Execute
        with patch('src.database.repository.execute_batch') as mock_execute:
            result = repo.insert_usernames_batch(usernames)
        
        # Assert
        assert mock_execute.called
    
    def test_get_usernames_by_status(self, mock_database_repository):
        """Test getting usernames by status"""
        # Setup
        repo = mock_database_repository
        conn, cursor = repo.conn, repo.cursor
        cursor.fetchall = Mock(return_value=[('user1',), ('user2',), ('user3',)])
        
        # Execute
        with patch.object(repo, 'get_cursor') as mock_cursor_ctx:
            mock_cursor_ctx.return_value.__enter__ = Mock(return_value=cursor)
            mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)
            usernames = repo.get_usernames_by_status(EnrichmentStatus.INITIAL, limit=10)
        
        # Assert
        assert cursor.execute.called
        assert len(usernames) == 3
    
    def test_claim_batch_for_processing(self, mock_database_repository):
        """Test claiming batch for parallel processing"""
        # Setup
        repo = mock_database_repository
        conn, cursor = repo.conn, repo.cursor
        cursor.fetchall = Mock(return_value=[('user1',), ('user2',)])
        cursor.rowcount = 0  # No stale records released
        
        # Execute
        with patch.object(repo, 'get_cursor') as mock_cursor_ctx:
            mock_cursor_ctx.return_value.__enter__ = Mock(return_value=cursor)
            mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)
            
            claimed = repo.claim_batch_for_processing(
                from_status=EnrichmentStatus.INITIAL,
                limit=50,
                instance_id='test-instance-123',
                timeout_minutes=30
            )
        
        # Assert
        assert cursor.execute.call_count >= 2  # One for stale release, one for claiming
        assert len(claimed) == 2
        assert 'user1' in claimed
        assert 'user2' in claimed
    
    def test_update_profile(self, mock_database_repository, sample_profile_data):
        """Test updating profile data"""
        # Setup
        repo = mock_database_repository
        conn, cursor = repo.conn, repo.cursor
        cursor.fetchone = Mock(return_value=(123,))  # Developer ID
        
        # Execute
        with patch.object(repo, 'get_cursor') as mock_cursor_ctx, \
             patch.object(repo, '_insert_social_links'), \
             patch.object(repo, '_insert_repositories'):
            
            mock_cursor_ctx.return_value.__enter__ = Mock(return_value=cursor)
            mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)
            
            developer_id = repo.update_profile(sample_profile_data)
        
        # Assert
        assert developer_id == 123
        assert cursor.execute.called
    
    def test_mark_as_failed(self, mock_database_repository):
        """Test marking developer as failed"""
        # Setup
        repo = mock_database_repository
        conn, cursor = repo.conn, repo.cursor
        
        # Execute
        with patch.object(repo, 'get_cursor') as mock_cursor_ctx:
            mock_cursor_ctx.return_value.__enter__ = Mock(return_value=cursor)
            mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)
            
            repo.mark_as_failed('test_user', 'API Error')
        
        # Assert
        assert cursor.execute.called
        # Verify the SQL includes claimed_by = NULL (for parallel execution)
        call_args = cursor.execute.call_args[0][0]
        assert 'FAILED' in call_args
        assert 'claimed_by' in call_args
    
    def test_increment_retry_count(self, mock_database_repository):
        """Test incrementing retry count"""
        # Setup
        repo = mock_database_repository
        conn, cursor = repo.conn, repo.cursor
        cursor.fetchone = Mock(return_value=(2,))  # Retry count
        
        # Execute
        with patch.object(repo, 'get_cursor') as mock_cursor_ctx:
            mock_cursor_ctx.return_value.__enter__ = Mock(return_value=cursor)
            mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)
            
            retry_count = repo.increment_retry_count(
                'test_user', 
                'Network error',
                EnrichmentStatus.INITIAL
            )
        
        # Assert
        assert retry_count == 2
        assert cursor.execute.called
    
    def test_get_stats(self, mock_database_repository):
        """Test getting database statistics"""
        # Setup
        repo = mock_database_repository
        conn, cursor = repo.conn, repo.cursor
        
        # Mock different queries returning different results
        cursor.fetchall = Mock(return_value=[
            ('INITIAL', 100),
            ('PROCESSING', 10),
            ('PROFILED', 50),
        ])
        cursor.fetchone = Mock(side_effect=[
            (160,),  # total_developers
            (25,),   # developers_with_email
            (30,),   # developers_with_social
            (75,),   # avg_followers
            (15,),   # avg_repos
            (5,),    # failed_count
        ])
        
        # Execute
        with patch.object(repo, 'get_cursor') as mock_cursor_ctx:
            mock_cursor_ctx.return_value.__enter__ = Mock(return_value=cursor)
            mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)
            
            stats = repo.get_stats()
        
        # Assert
        assert 'total_developers' in stats
        assert 'developers_with_email' in stats
        assert 'developers_with_social' in stats
    
    @patch('src.database.repository.settings')
    def test_parse_datetime(self, mock_settings):
        """Test datetime parsing"""
        # Setup mock settings to prevent initialization errors
        mock_db_config = Mock()
        mock_scraper_config = Mock()
        mock_settings.database = mock_db_config
        mock_settings.scraper = mock_scraper_config
        
        repo = DatabaseRepository()
        
        # Test valid ISO datetime
        dt = repo._parse_datetime('2025-01-01T12:00:00Z')
        assert dt is not None
        assert isinstance(dt, datetime)
        
        # Test None
        dt = repo._parse_datetime(None)
        assert dt is None
        
        # Test invalid format
        dt = repo._parse_datetime('invalid')
        assert dt is None
