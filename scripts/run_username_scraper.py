#!/usr/bin/env python3
"""
Run Username Scraper
Convenience script to run the username scraper
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.scrapers import UsernameScraper
from src.utils import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    try:
        scraper = UsernameScraper()
        scraper.run()
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
