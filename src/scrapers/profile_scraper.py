"""
Profile Scraper - Parallel Execution Support
Fetches GitHub profiles for users with INITIAL status and updates to PROFILED
Supports running multiple instances concurrently using row-level locking
"""
import time
import re
import os
import socket
from datetime import datetime
from github import RateLimitExceededException

from src.config import settings
from src.database import DatabaseRepository, EnrichmentStatus
from src.utils import get_logger, metrics, GitHubClientManager

logger = get_logger(__name__)


class ProfileScraper:
    """Scrape detailed GitHub profiles - supports parallel execution"""
    
    def __init__(self):
        self.github_client = GitHubClientManager()
        self.db = DatabaseRepository()
        self.config = settings.scraper
        self.scraper_name = 'profile_scraper'
        
        # Generate unique instance ID for parallel execution
        hostname = socket.gethostname()
        pid = os.getpid()
        self.instance_id = f"{hostname}-{pid}"
        
        logger.info(f"🚀 Profile Scraper initialized (instance: {self.instance_id})")
    
    def _extract_social_links(self, user):
        """Extract all social media links from profile"""
        social_links = {
            'twitter': None,
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
        }
        
        text_to_search = []
        if user.bio:
            text_to_search.append(user.bio)
        if user.blog:
            text_to_search.append(user.blog)
        if user.twitter_username:
            social_links['twitter'] = f"https://twitter.com/{user.twitter_username}"
        
        combined_text = ' '.join(text_to_search)
        
        patterns = {
            'twitter': r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)',
            'linkedin': r'(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9\-]+)',
            'facebook': r'(?:https?://)?(?:www\.)?facebook\.com/([a-zA-Z0-9\.]+)',
            'instagram': r'(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_\.]+)',
            'telegram': r'(?:https?://)?(?:t\.me|telegram\.me)/([a-zA-Z0-9_]+)',
            'youtube': r'(?:https?://)?(?:www\.)?youtube\.com/(?:c/|channel/|@)?([a-zA-Z0-9_\-]+)',
            'medium': r'(?:https?://)?(?:www\.)?medium\.com/@?([a-zA-Z0-9_\-]+)',
            'dev_to': r'(?:https?://)?(?:www\.)?dev\.to/([a-zA-Z0-9_\-]+)',
            'hashnode': r'(?:https?://)?([a-zA-Z0-9_\-]+)\.hashnode\.dev',
            'stackoverflow': r'(?:https?://)?(?:www\.)?stackoverflow\.com/users/([0-9]+)'
        }
        
        for platform, pattern in patterns.items():
            if social_links[platform]:
                continue
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                if platform == 'twitter':
                    social_links[platform] = f"https://twitter.com/{match.group(1)}"
                elif platform == 'linkedin':
                    social_links[platform] = f"https://linkedin.com/in/{match.group(1)}"
                elif platform == 'facebook':
                    social_links[platform] = f"https://facebook.com/{match.group(1)}"
                elif platform == 'instagram':
                    social_links[platform] = f"https://instagram.com/{match.group(1)}"
                elif platform == 'telegram':
                    social_links[platform] = f"https://t.me/{match.group(1)}"
                elif platform == 'youtube':
                    social_links[platform] = f"https://youtube.com/@{match.group(1)}"
                elif platform == 'medium':
                    social_links[platform] = f"https://medium.com/@{match.group(1)}"
                elif platform == 'dev_to':
                    social_links[platform] = f"https://dev.to/{match.group(1)}"
                elif platform == 'hashnode':
                    social_links[platform] = f"https://{match.group(1)}.hashnode.dev"
                elif platform == 'stackoverflow':
                    social_links[platform] = f"https://stackoverflow.com/users/{match.group(1)}"
        
        # Extract other URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        all_urls = re.findall(url_pattern, combined_text)
        
        known_domains = ['twitter.com', 'x.com', 'linkedin.com', 'facebook.com', 
                        'instagram.com', 't.me', 'telegram.me', 'youtube.com',
                        'medium.com', 'dev.to', 'hashnode.dev', 'stackoverflow.com']
        
        for url in all_urls:
            if not any(domain in url.lower() for domain in known_domains):
                if url not in social_links['other_links']:
                    social_links['other_links'].append(url)
        
        return social_links
    
    def fetch_profile(self, username: str):
        """Fetch detailed profile information for a user with retry logic"""
        for attempt in range(self.config.MAX_RETRIES):
            try:
                github = self.github_client.get_client()
                user = github.get_user(username)
                
                # Extract social links
                social_links = self._extract_social_links(user)
                
                # Get top repos
                top_repos = []
                repos = user.get_repos(sort='updated', direction='desc')
                
                for repo in list(repos)[:5]:
                    try:
                        top_repos.append({
                            'name': repo.name,
                            'stars': repo.stargazers_count,
                            'language': repo.language,
                            'url': repo.html_url,
                            'description': repo.description
                        })
                    except:
                        continue
                
                # Build profile dict
                profile = {
                    'username': user.login,
                    'name': user.name,
                    'email': user.email,
                    'bio': user.bio,
                    'location': user.location,
                    'company': user.company,
                    'blog': user.blog,
                    'twitter_username': user.twitter_username,
                    'hireable': user.hireable,
                    'followers': user.followers,
                    'following': user.following,
                    'public_repos': user.public_repos,
                    'public_gists': user.public_gists,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'updated_at': user.updated_at.isoformat() if user.updated_at else None,
                    'profile_url': user.html_url,
                    'avatar_url': user.avatar_url,
                    'social_links': social_links,
                    'top_repos': top_repos
                }
                
                return profile
            
            except RateLimitExceededException:
                metrics.increment(self.scraper_name, 'rate_limit')
                self.github_client.handle_rate_limit()
                metrics.increment(self.scraper_name, 'retries')
                continue
            
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}/{self.config.MAX_RETRIES} failed for {username}: {e}")
                metrics.increment(self.scraper_name, 'retries')
                
                if attempt < self.config.MAX_RETRIES - 1:
                    delay = self.config.RETRY_DELAY * (2 ** attempt if self.config.EXPONENTIAL_BACKOFF else 1)
                    time.sleep(delay)
                else:
                    # Mark as failed after max retries
                    self.db.mark_as_failed(username, str(e))
                    return None
        
        return None
    
    def scrape_profiles(self):
        """
        Fetch profiles for users with INITIAL status
        Uses claim-based approach for parallel execution support
        """
        logger.info("👤 Fetching profiles using claim-based approach (parallel-safe)...")
        
        profiled_count = self.db.get_username_count_by_status(EnrichmentStatus.PROFILED)
        logger.info(f"📊 Current PROFILED status count: {profiled_count}")
        
        if profiled_count >= self.config.TARGET_PROFILES:
            logger.info(f"✅ Already reached target of {self.config.TARGET_PROFILES} profiles!")
            return
        
        processed = 0
        batch_size = 50  # Claim 50 records at a time
        
        while True:
            # Check if target reached
            profiled_count = self.db.get_username_count_by_status(EnrichmentStatus.PROFILED)
            if profiled_count >= self.config.TARGET_PROFILES:
                logger.info(f"🎯 Target reached: {self.config.TARGET_PROFILES} profiles!")
                break
            
            # Claim a batch of usernames for this instance (parallel-safe)
            claimed_usernames = self.db.claim_batch_for_processing(
                from_status=EnrichmentStatus.INITIAL,
                limit=batch_size,
                instance_id=self.instance_id,
                timeout_minutes=30
            )
            
            if not claimed_usernames:
                logger.info("No more records to claim. Exiting.")
                break
            
            logger.info(f"Processing batch of {len(claimed_usernames)} usernames...")
            
            # Process each claimed username
            for username in claimed_usernames:
                try:
                    metrics.increment(self.scraper_name, 'processed')
                    profile = self.fetch_profile(username)
                    
                    if profile:
                        developer_id = self.db.update_profile(profile)
                        if developer_id:
                            processed += 1
                            metrics.increment(self.scraper_name, 'success')
                            
                            profiled_count = self.db.get_username_count_by_status(EnrichmentStatus.PROFILED)
                            
                            if processed % 10 == 0:
                                logger.info(f"  Progress - Processed: {processed}, Total PROFILED: {profiled_count}")
                            else:
                                logger.debug(f"  [{profiled_count}/{self.config.TARGET_PROFILES}] {username}")
                    else:
                        metrics.increment(self.scraper_name, 'failed')
                    
                    time.sleep(self.config.RATE_LIMIT_DELAY)
                
                except Exception as e:
                    logger.error(f"Error processing {username}: {e}")
                    metrics.increment(self.scraper_name, 'failed')
                    # Return to INITIAL status for retry by another instance
                    self.db.increment_retry_count(username, str(e), EnrichmentStatus.INITIAL)
                    continue
        
        logger.info(f"✅ Instance {self.instance_id} processed {processed} profiles")
    
    def run(self):
        """Main execution flow"""
        try:
            logger.info("=" * 70)
            logger.info("🚀 GitHub Profile Scraper")
            logger.info("=" * 70)
            
            # Connect to database
            self.db.connect()
            self.db.create_tables()
            
            # Scrape profiles
            self.scrape_profiles()
            
            # Show stats
            stats = self.db.get_stats()
            logger.info(f"\n📊 Database Statistics:")
            logger.info(f"  Total developers: {stats.get('total_developers', 0)}")
            logger.info(f"  INITIAL status: {stats.get('status_initial', 0)}")
            logger.info(f"  PROCESSING status: {stats.get('status_processing', 0)}")
            logger.info(f"  PROFILED status: {stats.get('status_profiled', 0)}")
            logger.info(f"  ENHANCED status: {stats.get('status_enhanced', 0)}")
            logger.info(f"  With email: {stats.get('developers_with_email', 0)}")
            logger.info(f"  With social: {stats.get('developers_with_social', 0)}")
            
            # Print metrics
            metrics.print_summary(self.scraper_name)
            
            logger.info("✅ Profile scraper completed!")
            
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
            raise
        finally:
            self.db.disconnect()


if __name__ == "__main__":
    try:
        scraper = ProfileScraper()
        scraper.run()
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user. Claims will be released automatically after timeout.")
        metrics.print_summary('profile_scraper')
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise
