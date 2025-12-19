"""
Scheduler for running scrapers on a schedule
Uses APScheduler for simple job scheduling
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import sys

from src.config import settings
from src.scrapers import UsernameScraper, ProfileScraper, SocialScraper
from src.utils import get_logger, metrics

logger = get_logger(__name__)


class ScraperScheduler:
    """Scheduler for running scrapers at configured intervals"""
    
    def __init__(self):
        self.scheduler = BlockingScheduler()
        self.config = settings.scheduler
        logger.info("🗓️  Scraper Scheduler initialized")
    
    def run_username_scraper(self):
        """Run username scraper job"""
        logger.info("=" * 70)
        logger.info(f"🚀 Starting scheduled USERNAME SCRAPER job at {datetime.now()}")
        logger.info("=" * 70)
        
        try:
            scraper = UsernameScraper()
            scraper.run()
            logger.info("✅ Username scraper job completed successfully")
        except Exception as e:
            logger.error(f"❌ Username scraper job failed: {e}", exc_info=True)
    
    def run_profile_scraper(self):
        """Run profile scraper job"""
        logger.info("=" * 70)
        logger.info(f"🚀 Starting scheduled PROFILE SCRAPER job at {datetime.now()}")
        logger.info("=" * 70)
        
        try:
            scraper = ProfileScraper()
            scraper.run()
            logger.info("✅ Profile scraper job completed successfully")
        except Exception as e:
            logger.error(f"❌ Profile scraper job failed: {e}", exc_info=True)
    
    def run_social_scraper(self):
        """Run social scraper job"""
        logger.info("=" * 70)
        logger.info(f"🚀 Starting scheduled SOCIAL SCRAPER job at {datetime.now()}")
        logger.info("=" * 70)
        
        try:
            scraper = SocialScraper()
            scraper.run()
            logger.info("✅ Social scraper job completed successfully")
        except Exception as e:
            logger.error(f"❌ Social scraper job failed: {e}", exc_info=True)
    
    def setup_jobs(self):
        """Setup scheduled jobs based on configuration"""
        if self.config.USE_CRON:
            # Use cron-style schedules
            logger.info("Using CRON schedules:")
            
            self.scheduler.add_job(
                self.run_username_scraper,
                trigger=CronTrigger.from_crontab(self.config.USERNAME_SCRAPER_SCHEDULE),
                id='username_scraper',
                name='Username Scraper',
                replace_existing=True
            )
            logger.info(f"  - Username Scraper: {self.config.USERNAME_SCRAPER_SCHEDULE}")
            
            self.scheduler.add_job(
                self.run_profile_scraper,
                trigger=CronTrigger.from_crontab(self.config.PROFILE_SCRAPER_SCHEDULE),
                id='profile_scraper',
                name='Profile Scraper',
                replace_existing=True
            )
            logger.info(f"  - Profile Scraper: {self.config.PROFILE_SCRAPER_SCHEDULE}")
            
            self.scheduler.add_job(
                self.run_social_scraper,
                trigger=CronTrigger.from_crontab(self.config.SOCIAL_SCRAPER_SCHEDULE),
                id='social_scraper',
                name='Social Scraper',
                replace_existing=True
            )
            logger.info(f"  - Social Scraper: {self.config.SOCIAL_SCRAPER_SCHEDULE}")
        
        else:
            # Use interval-based schedules
            logger.info("Using INTERVAL schedules:")
            
            self.scheduler.add_job(
                self.run_username_scraper,
                trigger=IntervalTrigger(seconds=self.config.USERNAME_SCRAPER_INTERVAL),
                id='username_scraper',
                name='Username Scraper',
                replace_existing=True
            )
            logger.info(f"  - Username Scraper: every {self.config.USERNAME_SCRAPER_INTERVAL}s ({self.config.USERNAME_SCRAPER_INTERVAL/3600:.1f}h)")
            
            self.scheduler.add_job(
                self.run_profile_scraper,
                trigger=IntervalTrigger(seconds=self.config.PROFILE_SCRAPER_INTERVAL),
                id='profile_scraper',
                name='Profile Scraper',
                replace_existing=True
            )
            logger.info(f"  - Profile Scraper: every {self.config.PROFILE_SCRAPER_INTERVAL}s ({self.config.PROFILE_SCRAPER_INTERVAL/3600:.1f}h)")
            
            self.scheduler.add_job(
                self.run_social_scraper,
                trigger=IntervalTrigger(seconds=self.config.SOCIAL_SCRAPER_INTERVAL),
                id='social_scraper',
                name='Social Scraper',
                replace_existing=True
            )
            logger.info(f"  - Social Scraper: every {self.config.SOCIAL_SCRAPER_INTERVAL}s ({self.config.SOCIAL_SCRAPER_INTERVAL/3600:.1f}h)")
    
    def start(self):
        """Start the scheduler"""
        logger.info("=" * 70)
        logger.info("🗓️  GitHub Scraper Scheduler")
        logger.info("=" * 70)
        
        self.setup_jobs()
        
        logger.info("\n✅ Scheduler started. Press Ctrl+C to stop.\n")
        logger.info("Upcoming jobs:")
        for job in self.scheduler.get_jobs():
            logger.info(f"  - {job.name}: next run at {job.next_run_time}")
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("\n⚠️  Scheduler stopped by user")
            self.scheduler.shutdown()


def main():
    """Main entry point"""
    try:
        scheduler = ScraperScheduler()
        scheduler.start()
    except Exception as e:
        logger.error(f"❌ Scheduler failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
