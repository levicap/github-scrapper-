"""
Show database statistics and scraper progress
"""
import os
from dotenv import load_dotenv
from src.database import DatabaseRepository

load_dotenv()


def main():
    """Display database statistics"""
    print("=" * 70)
    print("📊 GitHub Scraper Statistics")
    print("=" * 70)
    print()
    
    repo = DatabaseRepository()
    
    try:
        repo.connect()
        stats = repo.get_stats()
        
        # Status breakdown
        print("📈 Status Breakdown:")
        print(f"   INITIAL (not yet profiled): {stats.get('status_initial', 0):,}")
        print(f"   PROCESSING (being profiled): {stats.get('status_processing', 0):,}")
        print(f"   PROFILED (profile fetched): {stats.get('status_profiled', 0):,}")
        print(f"   ENHANCED (social enriched): {stats.get('status_enhanced', 0):,}")
        print(f"   FAILED: {stats.get('failed_count', 0):,}")
        print()
        
        # Totals
        print("📊 Totals:")
        print(f"   Total Developers: {stats.get('total_developers', 0):,}")
        print(f"   With Email: {stats.get('developers_with_email', 0):,}")
        print(f"   With Social Links: {stats.get('developers_with_social', 0):,}")
        print()
        
        # Averages
        print("📉 Averages:")
        print(f"   Avg Followers: {stats.get('avg_followers', 0):.1f}")
        print(f"   Avg Public Repos: {stats.get('avg_repos', 0):.1f}")
        print()
        
        # Progress
        total = stats.get('total_developers', 0)
        profiled = stats.get('status_profiled', 0) + stats.get('status_enhanced', 0)
        if total > 0:
            progress = (profiled / total) * 100
            print(f"🎯 Progress: {progress:.1f}% ({profiled:,} / {total:,})")
        
        # Active processing
        processing = stats.get('status_processing', 0)
        if processing > 0:
            print(f"\n⚙️  Currently processing: {processing} developers")
        
        print()
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        repo.disconnect()


if __name__ == '__main__':
    main()
