"""
Metrics collection for monitoring
Prometheus-style metrics tracking
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict
import threading
import time

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScraperMetrics:
    """Metrics for a single scraper"""
    total_processed: int = 0
    total_success: int = 0
    total_failed: int = 0
    total_retries: int = 0
    rate_limit_hits: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_processed == 0:
            return 0.0
        return (self.total_success / self.total_processed) * 100
    
    @property
    def processing_rate(self) -> float:
        """Calculate processing rate (items/hour)"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed == 0:
            return 0.0
        return (self.total_processed / elapsed) * 3600
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'total_processed': self.total_processed,
            'total_success': self.total_success,
            'total_failed': self.total_failed,
            'total_retries': self.total_retries,
            'rate_limit_hits': self.rate_limit_hits,
            'success_rate': round(self.success_rate, 2),
            'processing_rate': round(self.processing_rate, 2),
            'elapsed_seconds': (datetime.now() - self.start_time).total_seconds(),
            'start_time': self.start_time.isoformat(),
            'last_update': self.last_update.isoformat()
        }


class MetricsCollector:
    """
    Centralized metrics collector
    Thread-safe singleton pattern
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MetricsCollector, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.metrics: Dict[str, ScraperMetrics] = {
            'username_scraper': ScraperMetrics(),
            'profile_scraper': ScraperMetrics(),
            'social_scraper': ScraperMetrics()
        }
        self._initialized = True
        self.enabled = settings.metrics.ENABLED
        
        if self.enabled:
            logger.info("✅ Metrics collection enabled")
    
    def increment(self, scraper: str, metric: str, value: int = 1):
        """Increment a metric counter"""
        if not self.enabled:
            return
        
        with self._lock:
            if scraper in self.metrics:
                scraper_metrics = self.metrics[scraper]
                
                if metric == 'processed':
                    scraper_metrics.total_processed += value
                elif metric == 'success':
                    scraper_metrics.total_success += value
                elif metric == 'failed':
                    scraper_metrics.total_failed += value
                elif metric == 'retries':
                    scraper_metrics.total_retries += value
                elif metric == 'rate_limit':
                    scraper_metrics.rate_limit_hits += value
                
                scraper_metrics.last_update = datetime.now()
    
    def get_metrics(self, scraper: str = None) -> Dict:
        """Get metrics for a specific scraper or all scrapers"""
        if scraper:
            return self.metrics.get(scraper, ScraperMetrics()).to_dict()
        
        return {
            name: metrics.to_dict() 
            for name, metrics in self.metrics.items()
        }
    
    def reset(self, scraper: str = None):
        """Reset metrics for a scraper or all scrapers"""
        with self._lock:
            if scraper:
                self.metrics[scraper] = ScraperMetrics()
            else:
                for key in self.metrics:
                    self.metrics[key] = ScraperMetrics()
        
        logger.info(f"Metrics reset for {'all scrapers' if not scraper else scraper}")
    
    def print_summary(self, scraper: str = None):
        """Print metrics summary"""
        if scraper:
            scrapers_to_print = [scraper]
        else:
            scrapers_to_print = list(self.metrics.keys())
        
        print("\n" + "=" * 70)
        print("📊 METRICS SUMMARY")
        print("=" * 70)
        
        for name in scrapers_to_print:
            metrics = self.metrics[name]
            print(f"\n{name.upper().replace('_', ' ')}:")
            print(f"  Processed: {metrics.total_processed}")
            print(f"  Success: {metrics.total_success}")
            print(f"  Failed: {metrics.total_failed}")
            print(f"  Retries: {metrics.total_retries}")
            print(f"  Rate Limits: {metrics.rate_limit_hits}")
            print(f"  Success Rate: {metrics.success_rate:.2f}%")
            print(f"  Processing Rate: {metrics.processing_rate:.2f} items/hour")
        
        print("=" * 70 + "\n")
    
    def export_to_file(self, filepath: str):
        """Export metrics to JSON file"""
        import json
        
        with open(filepath, 'w') as f:
            json.dump(self.get_metrics(), f, indent=2)
        
        logger.info(f"Metrics exported to {filepath}")


# Lazy singleton instance - only instantiate when first accessed
_metrics_instance = None

def _get_metrics():
    """Get or create the metrics singleton instance"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance

# Create a proxy object that behaves like the MetricsCollector instance
class _MetricsProxy:
    """Proxy to delay MetricsCollector instantiation until first use"""
    def __getattr__(self, name):
        return getattr(_get_metrics(), name)
    
    def __repr__(self):
        return repr(_get_metrics())

metrics = _MetricsProxy()
