"""
Username Scraper
Searches for GitHub usernames and saves with INITIAL status
"""
import time
from datetime import datetime
from github import RateLimitExceededException

from src.config import settings
from src.database import DatabaseRepository, EnrichmentStatus
from src.utils import get_logger, metrics, GitHubClientManager

logger = get_logger(__name__)


class UsernameScraper:
    """Extract GitHub usernames and save with INITIAL status"""
    
    def __init__(self):
        self.github_client = GitHubClientManager()
        self.db = DatabaseRepository()
        self.config = settings.scraper
        self.scraper_name = 'username_scraper'
        
        logger.info("🚀 Username Scraper initialized")
    
    def search_users(self):
        """Search for users using location and date-based pagination"""
        logger.info(f"🔍 Starting username search (target: {self.config.TARGET_USERNAMES})...")
        
        total_searches = len(self.config.LOCATIONS) * len(self.config.years)
        search_count = 0
        batch_usernames = []
        
        # Get current count
        current_count = self.db.get_username_count_by_status(EnrichmentStatus.INITIAL)
        logger.info(f"📊 Current INITIAL status count: {current_count}")
        
        for location in self.config.LOCATIONS:
            for year in self.config.years:
                # Check if we have enough
                current_count = self.db.get_username_count_by_status(EnrichmentStatus.INITIAL)
                if current_count >= self.config.TARGET_USERNAMES:
                    logger.info(f"✅ Reached target of {self.config.TARGET_USERNAMES} usernames!")
                    break
                
                search_count += 1
                query = f"location:{location} created:{year}-01-01..{year}-12-31 type:user"
                
                try:
                    github = self.github_client.get_client()
                    users = github.search_users(query=query)
                    count = 0
                    
                    for user in users:
                        batch_usernames.append(user.login)
                        count += 1
                        metrics.increment(self.scraper_name, 'processed')
                        
                        # Save batch
                        if len(batch_usernames) >= self.config.BATCH_SIZE:
                            inserted = self.db.insert_usernames_batch(batch_usernames)
                            metrics.increment(self.scraper_name, 'success', inserted)
                            batch_usernames = []
                        
                        # Check target
                        current_count = self.db.get_username_count_by_status(EnrichmentStatus.INITIAL)
                        if current_count >= self.config.TARGET_USERNAMES:
                            break
                        
                        # GitHub search max
                        if count >= settings.github.SEARCH_MAX_RESULTS:
                            break
                    
                    # Save remaining
                    if batch_usernames:
                        inserted = self.db.insert_usernames_batch(batch_usernames)
                        metrics.increment(self.scraper_name, 'success', inserted)
                        batch_usernames = []
                    
                    current_count = self.db.get_username_count_by_status(EnrichmentStatus.INITIAL)
                    logger.info(f"  [{search_count}/{total_searches}] {location} {year}: +{count} users (total: {current_count})")
                    
                    time.sleep(self.config.RATE_LIMIT_DELAY)
                
                except RateLimitExceededException:
                    # Save batch before rotating
                    if batch_usernames:
                        inserted = self.db.insert_usernames_batch(batch_usernames)
                        metrics.increment(self.scraper_name, 'success', inserted)
                        batch_usernames = []
                    
                    metrics.increment(self.scraper_name, 'rate_limit')
                    self.github_client.handle_rate_limit()
                    continue
                
                except Exception as e:
                    logger.error(f"Error searching {location} {year}: {e}")
                    metrics.increment(self.scraper_name, 'failed')
                    time.sleep(self.config.RATE_LIMIT_DELAY)
                    continue
            
            # Break outer loop
            current_count = self.db.get_username_count_by_status(EnrichmentStatus.INITIAL)
            if current_count >= self.config.TARGET_USERNAMES:
                break
        
        # Final save
        if batch_usernames:
            inserted = self.db.insert_usernames_batch(batch_usernames)
            metrics.increment(self.scraper_name, 'success', inserted)
        
        final_count = self.db.get_username_count_by_status(EnrichmentStatus.INITIAL)
        logger.info(f"✅ Total usernames with INITIAL status: {final_count}")
    
    def run(self):
        """Main execution flow"""
        try:
            logger.info("=" * 70)
            logger.info("🚀 GitHub Username Scraper")
            logger.info("=" * 70)
            
            # Connect to database
            self.db.connect()
            self.db.create_tables()
            
            # Search for usernames
            self.search_users()
            
            # Show stats
            stats = self.db.get_stats()
            logger.info(f"\n📊 Database Statistics:")
            logger.info(f"  Total developers: {stats.get('total_developers', 0)}")
            logger.info(f"  INITIAL status: {stats.get('status_initial', 0)}")
            logger.info(f"  PROFILED status: {stats.get('status_profiled', 0)}")
            logger.info(f"  ENHANCED status: {stats.get('status_enhanced', 0)}")
            
            # Print metrics
            metrics.print_summary(self.scraper_name)
            
            logger.info("✅ Username scraper completed!")
            
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
            raise
        finally:
            self.db.disconnect()


if __name__ == "__main__":
    try:
        scraper = UsernameScraper()
        scraper.run()
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user. Progress saved to database.")
        metrics.print_summary('username_scraper')
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise
