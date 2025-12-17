#!/usr/bin/env python3
"""
GitHub Scraper - Main Script
Runs both username extraction and profile scraping sequentially.
"""

import sys
import time
from datetime import datetime

# Import the scraper classes
from extract_usernames import UsernameExtractor
from scrape_profiles import ProfileScraper


def print_banner():
    """Print a nice banner"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║           GitHub Ukrainian Developers Scraper                ║
║                     Complete Workflow                         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_section(title):
    """Print a section separator"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def main():
    """Main execution flow"""
    start_time = time.time()
    
    try:
        print_banner()
        print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # ============================================
        # PHASE 1: Extract Usernames
        # ============================================
        print_section("PHASE 1: Extracting Usernames")
        
        print("📋 This phase will search GitHub for Ukrainian developers")
        print("📋 Target: 12,000 usernames (10k + 20% buffer)")
        print("📋 Estimated time: 30-60 minutes\n")
        
        input("Press Enter to start Phase 1... ")
        
        phase1_start = time.time()
        
        try:
            extractor = UsernameExtractor()
            extractor.run()
            
            phase1_time = (time.time() - phase1_start) / 60
            print(f"\n✅ Phase 1 completed in {phase1_time:.1f} minutes")
            
        except Exception as e:
            print(f"\n❌ Phase 1 failed: {e}")
            print("\nYou can restart the script - it will resume from where it left off.")
            return 1
        
        # ============================================
        # PHASE 2: Scrape Profiles
        # ============================================
        print_section("PHASE 2: Scraping Detailed Profiles")
        
        print("👤 This phase will fetch detailed profiles for each username")
        print("👤 Target: 10,000 profiles")
        print("👤 Estimated time: 3-5 hours\n")
        
        proceed = input("Press Enter to start Phase 2 (or 'q' to quit): ")
        
        if proceed.lower() == 'q':
            print("\n⏸️  Stopping here. Run this script again to continue with Phase 2.")
            return 0
        
        phase2_start = time.time()
        
        try:
            scraper = ProfileScraper()
            scraper.run()
            
            phase2_time = (time.time() - phase2_start) / 60
            print(f"\n✅ Phase 2 completed in {phase2_time:.1f} minutes")
            
        except Exception as e:
            print(f"\n❌ Phase 2 failed: {e}")
            print("\nYou can restart the script - it will resume from where it left off.")
            return 1
        
        # ============================================
        # COMPLETE
        # ============================================
        total_time = (time.time() - start_time) / 60
        
        print_section("SCRAPING COMPLETE!")
        
        print(f"✅ Total time: {total_time:.1f} minutes ({total_time/60:.1f} hours)")
        print(f"✅ Phase 1 time: {phase1_time:.1f} minutes")
        print(f"✅ Phase 2 time: {phase2_time:.1f} minutes")
        print(f"\n📁 All data saved to PostgreSQL database: github_developers")
        print(f"\n🎉 Scraping completed successfully!")
        
        # Print final stats
        print("\n📊 Final Statistics:")
        print("   Run this query to see your data:")
        print("   docker exec -it postgres_db psql -U ahmed -d github_developers")
        print("   SELECT COUNT(*) FROM developers;")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print("Progress has been saved to database.")
        print("Run this script again to continue from where you left off.")
        return 1
    
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())