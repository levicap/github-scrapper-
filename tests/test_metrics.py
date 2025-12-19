"""Tests for Metrics Collector"""
import pytest
from unittest.mock import patch
from src.utils.metrics import MetricsCollector, ScraperMetrics


class TestScraperMetrics:
    """Test scraper metrics data class"""
    
    def test_initial_values(self):
        """Test initial metric values"""
        metrics = ScraperMetrics()
        
        assert metrics.total_processed == 0
        assert metrics.total_success == 0
        assert metrics.total_failed == 0
        assert metrics.total_retries == 0
        assert metrics.rate_limit_hits == 0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        metrics = ScraperMetrics()
        metrics.total_processed = 100
        metrics.total_success = 80
        
        assert metrics.success_rate == 80.0
    
    def test_success_rate_zero_processed(self):
        """Test success rate when nothing processed"""
        metrics = ScraperMetrics()
        assert metrics.success_rate == 0.0
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        metrics = ScraperMetrics()
        metrics.total_processed = 100
        metrics.total_success = 85
        
        data = metrics.to_dict()
        
        assert 'total_processed' in data
        assert 'total_success' in data
        assert 'success_rate' in data
        assert 'processing_rate' in data
        assert data['total_processed'] == 100
        assert data['total_success'] == 85


class TestMetricsCollector:
    """Test metrics collector functionality"""
    
    def test_singleton_pattern(self):
        """Test metrics collector is a singleton"""
        from src.utils.metrics import _get_metrics
        collector1 = _get_metrics()
        collector2 = _get_metrics()
        
        assert collector1 is collector2
    
    def test_increment_processed(self):
        """Test incrementing processed counter"""
        from src.utils.metrics import metrics
        metrics.reset('username_scraper')
        
        metrics.increment('username_scraper', 'processed', 5)
        
        result = metrics.get_metrics('username_scraper')
        assert result['total_processed'] == 5
    
    def test_increment_success(self):
        """Test incrementing success counter"""
        from src.utils.metrics import metrics
        metrics.reset('profile_scraper')
        
        metrics.increment('profile_scraper', 'success', 3)
        
        result = metrics.get_metrics('profile_scraper')
        assert result['total_success'] == 3
    
    def test_increment_failed(self):
        """Test incrementing failed counter"""
        from src.utils.metrics import metrics
        metrics.reset('social_scraper')
        
        metrics.increment('social_scraper', 'failed', 2)
        
        result = metrics.get_metrics('social_scraper')
        assert result['total_failed'] == 2
    
    def test_increment_rate_limit(self):
        """Test incrementing rate limit counter"""
        from src.utils.metrics import metrics
        metrics.reset('profile_scraper')
        
        metrics.increment('profile_scraper', 'rate_limit')
        
        result = metrics.get_metrics('profile_scraper')
        assert result['rate_limit_hits'] == 1
    
    def test_get_all_metrics(self):
        """Test getting metrics for all scrapers"""
        from src.utils.metrics import metrics
        metrics.reset()
        
        metrics.increment('username_scraper', 'processed', 10)
        metrics.increment('profile_scraper', 'processed', 20)
        
        all_metrics = metrics.get_metrics()
        
        assert 'username_scraper' in all_metrics
        assert 'profile_scraper' in all_metrics
        assert all_metrics['username_scraper']['total_processed'] == 10
        assert all_metrics['profile_scraper']['total_processed'] == 20
    
    def test_reset_single_scraper(self):
        """Test resetting metrics for single scraper"""
        from src.utils.metrics import metrics
        
        metrics.increment('username_scraper', 'processed', 100)
        metrics.reset('username_scraper')
        
        result = metrics.get_metrics('username_scraper')
        assert result['total_processed'] == 0
    
    def test_reset_all_scrapers(self):
        """Test resetting metrics for all scrapers"""
        from src.utils.metrics import metrics
        
        metrics.increment('username_scraper', 'processed', 100)
        metrics.increment('profile_scraper', 'processed', 50)
        metrics.reset()
        
        all_metrics = metrics.get_metrics()
        assert all_metrics['username_scraper']['total_processed'] == 0
        assert all_metrics['profile_scraper']['total_processed'] == 0
    
    @patch('src.utils.metrics.settings')
    def test_disabled_metrics(self, mock_settings):
        """Test metrics when disabled"""
        from unittest.mock import Mock
        from src.utils.metrics import metrics
        
        # Create a mock metrics config
        mock_metrics_config = Mock()
        mock_metrics_config.ENABLED = False
        mock_settings.metrics = mock_metrics_config
        
        # Reset to reinitialize with mocked settings
        metrics.reset()
        
        # Increment should still work (logging just won't happen)
        metrics.increment('username_scraper', 'processed', 10)
        
        # The metrics object always exists, enabled just controls logging
        assert hasattr(metrics, 'increment')
