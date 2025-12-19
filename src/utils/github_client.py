"""
GitHub API client manager
Handles token rotation and rate limiting
"""
from github import Github, RateLimitExceededException, Auth
from typing import List
import time

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GitHubClientManager:
    """Manage GitHub API clients with token rotation"""
    
    def __init__(self):
        self.tokens: List[str] = settings.github.TOKENS
        self.current_token_index = 0
        self.github = self._create_client(self.tokens[0])
        
        logger.info(f"✅ GitHub client initialized with {len(self.tokens)} token(s)")
    
    def _create_client(self, token: str) -> Github:
        """Create GitHub client with authentication"""
        auth = Auth.Token(token)
        return Github(auth=auth)
    
    def get_client(self) -> Github:
        """Get current GitHub client"""
        return self.github
    
    def rotate_token(self):
        """Rotate to next available token"""
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        self.github = self._create_client(self.tokens[self.current_token_index])
        logger.info(f"🔄 Rotated to token {self.current_token_index + 1}/{len(self.tokens)}")
    
    def handle_rate_limit(self):
        """Handle rate limit by rotating token and waiting"""
        logger.warning("⚠️  Rate limit hit, rotating tokens...")
        self.rotate_token()
        time.sleep(settings.scraper.TOKEN_ROTATION_DELAY)
    
    def get_rate_limit_info(self) -> dict:
        """Get current rate limit information"""
        try:
            rate_limit = self.github.get_rate_limit()
            return {
                'core': {
                    'remaining': rate_limit.core.remaining,
                    'limit': rate_limit.core.limit,
                    'reset': rate_limit.core.reset
                },
                'search': {
                    'remaining': rate_limit.search.remaining,
                    'limit': rate_limit.search.limit,
                    'reset': rate_limit.search.reset
                }
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit info: {e}")
            return {}
