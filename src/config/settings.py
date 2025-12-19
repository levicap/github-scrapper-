"""
Configuration settings for GitHub Scraper
All configurable constants in one place
"""
import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ScraperConfig:
    """Scraper-specific configuration"""
    
    # Location targeting
    LOCATIONS: List[str] = None
    
    # Time ranges
    YEARS_START: int = 2015
    YEARS_END: int = 2025
    
    # Targets
    TARGET_USERNAMES: int = 12000
    TARGET_PROFILES: int = 10000
    
    # Batch processing
    BATCH_SIZE: int = 100
    CHECKPOINT_INTERVAL: int = 50
    
    # Rate limiting
    RATE_LIMIT_DELAY: int = 2  # seconds between requests
    TOKEN_ROTATION_DELAY: int = 60  # seconds to wait after rate limit
    
    # Retry configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5  # seconds
    EXPONENTIAL_BACKOFF: bool = True
    
    def __post_init__(self):
        if self.LOCATIONS is None:
            self.LOCATIONS = [
                "Kyiv", "Kiev", "Kharkiv", "Kharkov", "Odesa", "Odessa",
                "Dnipro", "Dnipropetrovsk", "Lviv", "Lvov", "Zaporizhzhia",
                "Kryvyi Rih", "Mykolaiv", "Mariupol", "Vinnytsia", "Kherson",
                "Poltava", "Ukraine"
            ]
    
    @property
    def years(self) -> List[int]:
        """Get list of years to scrape"""
        return list(range(self.YEARS_START, self.YEARS_END))


@dataclass
class DatabaseConfig:
    """Database configuration"""
    
    HOST: str = os.getenv('DB_HOST', 'localhost')
    PORT: str = os.getenv('DB_PORT', '5432')
    NAME: str = os.getenv('DB_NAME', 'github_developers')
    USER: str = os.getenv('DB_USER', 'ahmed')
    PASSWORD: str = os.getenv('DB_PASSWORD', 'ahmed123')
    
    # Connection pool settings
    MIN_CONNECTIONS: int = 1
    MAX_CONNECTIONS: int = 10
    
    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return f"postgresql://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.NAME}"
    
    @property
    def config_dict(self) -> dict:
        """Get config as dictionary for psycopg2"""
        return {
            'host': self.HOST,
            'port': self.PORT,
            'database': self.NAME,
            'user': self.USER,
            'password': self.PASSWORD
        }


@dataclass
class GitHubConfig:
    """GitHub API configuration"""
    
    # Load tokens from environment
    TOKENS: List[str] = None
    
    # API limits
    SEARCH_MAX_RESULTS: int = 1000  # GitHub API limitation
    
    def __post_init__(self):
        """Load GitHub tokens from environment"""
        if self.TOKENS is None:
            tokens = []
            for i in range(1, 10):
                token_key = f"GITHUB_TOKEN_{i}" if i > 1 else "GITHUB_TOKEN"
                token = os.getenv(token_key)
                if token:
                    tokens.append(token)
            
            if not tokens:
                raise ValueError("No GitHub tokens found! Set GITHUB_TOKEN in .env file")
            
            self.TOKENS = tokens


@dataclass
class MetricsConfig:
    """Metrics and monitoring configuration"""
    
    ENABLED: bool = True
    PORT: int = 9090
    EXPORT_INTERVAL: int = 60  # seconds
    
    # Prometheus push gateway (optional)
    PUSH_GATEWAY_URL: str = os.getenv('PROMETHEUS_PUSH_GATEWAY', None)


@dataclass
class SchedulerConfig:
    """Scheduler configuration"""
    
    # Cron-like schedules (can be configured)
    USERNAME_SCRAPER_SCHEDULE: str = "0 0 * * *"  # Daily at midnight
    PROFILE_SCRAPER_SCHEDULE: str = "0 2 * * *"   # Daily at 2 AM
    SOCIAL_SCRAPER_SCHEDULE: str = "0 4 * * *"    # Daily at 4 AM
    
    # Or simple intervals (in seconds)
    USE_CRON: bool = False  # If False, use intervals
    USERNAME_SCRAPER_INTERVAL: int = 86400  # 24 hours
    PROFILE_SCRAPER_INTERVAL: int = 86400   # 24 hours
    SOCIAL_SCRAPER_INTERVAL: int = 86400    # 24 hours


class Settings:
    """Main settings class - singleton pattern"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.scraper = ScraperConfig()
        self.database = DatabaseConfig()
        self.github = GitHubConfig()
        self.metrics = MetricsConfig()
        self.scheduler = SchedulerConfig()
        
        self._initialized = True
    
    def __repr__(self):
        return (
            f"Settings(\n"
            f"  Scraper: {self.scraper.TARGET_PROFILES} profiles target\n"
            f"  Database: {self.database.HOST}:{self.database.PORT}/{self.database.NAME}\n"
            f"  GitHub: {len(self.github.TOKENS)} token(s)\n"
            f"  Metrics: {'Enabled' if self.metrics.ENABLED else 'Disabled'}\n"
            f")"
        )


# Singleton instance
settings = Settings()
