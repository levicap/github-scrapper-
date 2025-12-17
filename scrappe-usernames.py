#!/usr/bin/env python3
"""
GitHub Username Extractor - Database Version
Searches for Ukrainian developers and saves usernames directly to PostgreSQL.
"""

import os
import time
from datetime import datetime
from typing import Set
from github import Github, RateLimitExceededException, Auth
from dotenv import load_dotenv
from dbutils import DatabaseManager

# Load environment variables
load_dotenv()

# Configuration
TARGET_USERNAMES = 12000  # 10k + 20% buffer

# Ukrainian cities (with aliases)
LOCATIONS = [
    "Kyiv", "Kiev", "Kharkiv", "Kharkov", "Odesa", "Odessa",
    "Dnipro", "Dnipropetrovsk", "Lviv", "Lvov", "Zaporizhzhia",
    "Kryvyi Rih", "Mykolaiv", "Mariupol", "Vinnytsia", "Kherson",
    "Poltava", "Ukraine"
]

# Date ranges (years to search)
YEARS = list(range(2015, 2025))  # 2015-2024


class UsernameExtractor:
    """Extract GitHub usernames for Ukrainian developers"""
    
    def __init__(self):
        self.tokens = self._load_tokens()
        self.current_token_index = 0
        auth = Auth.Token(self.tokens[0])
        self.github = Github(auth=auth)
        self.db = DatabaseManager()
        
    def _load_tokens(self):
        """Load GitHub tokens from environment"""
        tokens = []
        for i in range(1, 10):  # Support up to 9 tokens
            token_key = f"GITHUB_TOKEN_{i}" if i > 1 else "GITHUB_TOKEN"
            token = os.getenv(token_key)
            if token:
                tokens.append(token)
        
        if not tokens:
            raise ValueError("No GitHub tokens found! Set GITHUB_TOKEN in .env file")
        
        print(f"✅ Loaded {len(tokens)} GitHub token(s)")
        return tokens
    
    def _rotate_token(self):
        """Rotate to next available token"""
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        auth = Auth.Token(self.tokens[self.current_token_index])
        self.github = Github(auth=auth)
        print(f"🔄 Rotated to token {self.current_token_index + 1}/{len(self.tokens)}")
    
    def search_users(self):
        """Search for Ukrainian developers using date-based pagination"""
        total_searches = len(LOCATIONS) * len(YEARS)
        search_count = 0
        batch_usernames = []
        BATCH_SIZE = 100  # Save to DB every 100 usernames
        
        print(f"\n🔍 Searching for usernames (target: {TARGET_USERNAMES})...")
        print("=" * 60)
        
        # Get current count from database
        current_count = self.db.get_username_count()
        print(f"📊 Current database count: {current_count}")
        
        for location in LOCATIONS:
            for year in YEARS:
                # Check if we have enough usernames
                current_count = self.db.get_username_count()
                if current_count >= TARGET_USERNAMES:
                    print(f"\n✅ Reached target of {TARGET_USERNAMES} usernames!")
                    break
                
                search_count += 1
                query = f"location:{location} created:{year}-01-01..{year}-12-31 type:user"
                
                try:
                    # Perform search - PyGithub handles rate limiting automatically
                    users = self.github.search_users(query=query)
                    count = 0
                    
                    for user in users:
                        batch_usernames.append(user.login)
                        count += 1
                        
                        # Save batch to database
                        if len(batch_usernames) >= BATCH_SIZE:
                            self.db.insert_usernames_batch(batch_usernames)
                            batch_usernames = []
                        
                        # Stop if we have enough
                        current_count = self.db.get_username_count()
                        if current_count >= TARGET_USERNAMES:
                            break
                        
                        # GitHub search maxes out at 1000 results
                        if count >= 1000:
                            break
                    
                    # Save remaining batch
                    if batch_usernames:
                        self.db.insert_usernames_batch(batch_usernames)
                        batch_usernames = []
                    
                    current_count = self.db.get_username_count()
                    print(f"  [{search_count}/{total_searches}] {location} {year}: +{count} users (total: {current_count})")
                    
                    # Brief pause to be nice to API
                    time.sleep(2)
                
                except RateLimitExceededException:
                    # Save any remaining usernames before rotating
                    if batch_usernames:
                        self.db.insert_usernames_batch(batch_usernames)
                        batch_usernames = []
                    
                    print(f"⚠️  Rate limit hit, rotating tokens...")
                    self._rotate_token()
                    time.sleep(60)
                    continue
                
                except Exception as e:
                    print(f"❌ Error searching {location} {year}: {e}")
                    time.sleep(2)
                    continue
            
            # Break outer loop too if we have enough
            current_count = self.db.get_username_count()
            if current_count >= TARGET_USERNAMES:
                break
        
        # Save any remaining usernames
        if batch_usernames:
            self.db.insert_usernames_batch(batch_usernames)
        
        final_count = self.db.get_username_count()
        print("\n" + "=" * 60)
        print(f"✅ Total usernames in database: {final_count}")
    
    def run(self):
        """Main execution flow"""
        try:
            print("🚀 GitHub Username Extractor - Database Version")
            print("=" * 60)
            
            # Connect to database
            self.db.connect()
            
            # Create tables if they don't exist
            self.db.create_tables()
            
            # Search for usernames
            self.search_users()
            
            # Show stats
            stats = self.db.get_stats()
            print(f"\n📊 Database Statistics:")
            print(f"  Total usernames: {stats.get('total_usernames', 0)}")
            
            print(f"\n✅ COMPLETE!")
            print(f"📁 Data saved to PostgreSQL database: github_developers")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            raise
        finally:
            self.db.disconnect()


if __name__ == "__main__":
    try:
        extractor = UsernameExtractor()
        extractor.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Progress has been saved to database.")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        raise