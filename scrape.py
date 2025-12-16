#!/usr/bin/env python3
"""
GitHub Ukrainian Developers Scraper - Demo Version
Collects Ukrainian developer profiles with date-based pagination and token rotation.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Set
from github import Github, GithubException, RateLimitExceededException, Auth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TARGET_PROFILES = 10000
CHECKPOINT_INTERVAL = 50
OUTPUT_FILE = "ukrainian_developers.json"

# Ukrainian cities (with aliases)
LOCATIONS = [
    "Kyiv", "Kiev", "Kharkiv", "Kharkov", "Odesa", "Odessa",
    "Dnipro", "Dnipropetrovsk", "Lviv", "Lvov", "Zaporizhzhia",
    "Kryvyi Rih", "Mykolaiv", "Mariupol", "Vinnytsia", "Kherson",
    "Poltava", "Ukraine"
]

# Date ranges (years to search)
YEARS = list(range(2015, 2025))  # 2015-2024


class GitHubScraper:
    """GitHub scraper with token rotation and resume capability"""
    
    def __init__(self):
        self.tokens = self._load_tokens()
        self.current_token_index = 0
        auth = Auth.Token(self.tokens[0])
        self.github = Github(auth=auth)
        self.scraped_usernames: Set[str] = set()
        self.profiles: List[Dict] = []
        
    def _load_tokens(self) -> List[str]:
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
    
    def _check_rate_limit(self, api_type='search'):
        """Check rate limit and wait if necessary"""
        try:
            rate_limit = self.github.get_rate_limit()
            
            # Access rate limit based on type
            if api_type == 'search':
                rate = rate_limit.search
                limit_name = "Search"
            else:
                rate = rate_limit.core
                limit_name = "Core"
            
            remaining = rate.remaining
            reset_time = rate.reset
            
            # If low on requests, try rotating token
            if remaining < 5:
                print(f"⚠️  {limit_name} API limit low ({remaining} remaining)")
                
                # Try other tokens
                original_index = self.current_token_index
                for _ in range(len(self.tokens) - 1):
                    self._rotate_token()
                    
                    try:
                        rate_limit = self.github.get_rate_limit()
                        rate = rate_limit.search if api_type == 'search' else rate_limit.core
                        remaining = rate.remaining
                        
                        if remaining > 10:
                            print(f"✅ Found token with {remaining} requests remaining")
                            return
                    except:
                        continue
                
                # All tokens exhausted, wait for reset
                self.current_token_index = original_index
                auth = Auth.Token(self.tokens[self.current_token_index])
                self.github = Github(auth=auth)
                
                wait_seconds = (reset_time - datetime.utcnow()).total_seconds() + 10
                if wait_seconds > 0:
                    print(f"⏳ All tokens exhausted. Waiting {wait_seconds/60:.1f} minutes...")
                    time.sleep(wait_seconds)
        
        except AttributeError as e:
            # Rate limit structure different - skip check and rely on PyGithub's built-in handling
            pass
        except Exception as e:
            print(f"⚠️  Rate limit check error: {e}")
            time.sleep(2)
    
    def search_users(self) -> Set[str]:
        """Search for Ukrainian developers using date-based pagination"""
        all_usernames = set()
        total_searches = len(LOCATIONS) * len(YEARS)
        search_count = 0
        
        print(f"\n🔍 Phase 1: Searching for usernames across {total_searches} queries...")
        
        for location in LOCATIONS:
            for year in YEARS:
                search_count += 1
                query = f"location:{location} created:{year}-01-01..{year}-12-31 type:user"
                
                try:
                    # Perform search - PyGithub handles rate limiting automatically
                    users = self.github.search_users(query=query)
                    count = 0
                    
                    for user in users:
                        all_usernames.add(user.login)
                        count += 1
                        
                        # GitHub search maxes out at 1000 results
                        if count >= 1000:
                            break
                    
                    print(f"  [{search_count}/{total_searches}] {location} {year}: +{count} users (total: {len(all_usernames)})")
                    
                    # Save intermediate results after each query
                    self._save_search_progress(all_usernames, search_count, total_searches)
                    
                    # Brief pause to be nice to API
                    time.sleep(2)
                
                except RateLimitExceededException:
                    print(f"⚠️  Rate limit hit, rotating tokens...")
                    self._rotate_token()
                    time.sleep(60)
                    continue
                
                except Exception as e:
                    print(f"❌ Error searching {location} {year}: {e}")
                    time.sleep(2)
                    continue
        
        print(f"\n✅ Found {len(all_usernames)} unique usernames")
        return all_usernames
    
    def _save_search_progress(self, usernames: Set[str], completed: int, total: int):
        """Save search progress to intermediate file"""
        try:
            progress_file = "search_progress.json"
            progress_data = {
                'metadata': {
                    'queries_completed': completed,
                    'total_queries': total,
                    'progress_percentage': f"{(completed/total)*100:.1f}%",
                    'unique_usernames_found': len(usernames),
                    'last_updated': datetime.utcnow().isoformat()
                },
                'usernames': sorted(list(usernames))
            }
            
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f"⚠️  Failed to save search progress: {e}")
    
    def fetch_profile(self, username: str) -> Dict:
        """Fetch detailed profile information for a user"""
        try:
            user = self.github.get_user(username)
            
            # Get top 5 repos
            top_repos = []
            repos = user.get_repos(sort='updated', direction='desc')
            
            for repo in list(repos)[:5]:
                try:
                    top_repos.append({
                        'name': repo.name,
                        'stars': repo.stargazers_count,
                        'language': repo.language,
                        'url': repo.html_url
                    })
                except:
                    continue
            
            # Build profile data
            profile = {
                'username': user.login,
                'name': user.name,
                'email': user.email,
                'bio': user.bio,
                'location': user.location,
                'company': user.company,
                'blog': user.blog,
                'followers': user.followers,
                'following': user.following,
                'public_repos': user.public_repos,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None,
                'top_repos': top_repos,
                'scraped_at': datetime.utcnow().isoformat()
            }
            
            return profile
        
        except Exception as e:
            print(f"❌ Failed to fetch {username}: {e}")
            return None
    
    def load_checkpoint(self):
        """Load existing progress from file"""
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.profiles = data.get('profiles', [])
                    self.scraped_usernames = {p['username'] for p in self.profiles}
                
                print(f"📂 Loaded {len(self.profiles)} existing profiles")
            except Exception as e:
                print(f"⚠️  Could not load checkpoint: {e}")
    
    def save_checkpoint(self):
        """Save progress to file"""
        try:
            output = {
                'metadata': {
                    'total_profiles': len(self.profiles),
                    'last_updated': datetime.utcnow().isoformat(),
                    'target': TARGET_PROFILES
                },
                'profiles': self.profiles
            }
            
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Checkpoint saved: {len(self.profiles)} profiles")
        
        except Exception as e:
            print(f"❌ Failed to save checkpoint: {e}")
    
    def scrape_profiles(self, usernames: Set[str]):
        """Fetch detailed profiles for all usernames"""
        # Filter out already scraped
        remaining = usernames - self.scraped_usernames
        print(f"\n👤 Phase 2: Fetching profiles for {len(remaining)} users...")
        
        if len(self.profiles) >= TARGET_PROFILES:
            print(f"✅ Already reached target of {TARGET_PROFILES} profiles!")
            return
        
        start_time = time.time()
        count = 0
        
        for username in remaining:
            # Check if we've hit target
            if len(self.profiles) >= TARGET_PROFILES:
                print(f"\n🎯 Target reached: {TARGET_PROFILES} profiles!")
                break
            
            try:
                # Fetch profile - PyGithub handles rate limiting
                profile = self.fetch_profile(username)
                
                if profile:
                    self.profiles.append(profile)
                    self.scraped_usernames.add(username)
                    count += 1
                    
                    # Progress update
                    elapsed = time.time() - start_time
                    rate = count / (elapsed / 3600) if elapsed > 0 else 0
                    
                    print(f"  [{len(self.profiles)}/{TARGET_PROFILES}] {username} | Rate: {rate:.1f}/hour")
                    
                    # Checkpoint every N profiles
                    if count % CHECKPOINT_INTERVAL == 0:
                        self.save_checkpoint()
                
                # Brief pause
                time.sleep(1)
                
            except RateLimitExceededException:
                print(f"⚠️  Rate limit hit, rotating tokens...")
                self._rotate_token()
                time.sleep(60)
                continue
            
            except Exception as e:
                print(f"❌ Error with {username}: {e}")
                time.sleep(1)
                continue
        
        # Final save
        self.save_checkpoint()
        
        elapsed = time.time() - start_time
        print(f"\n✅ Scraped {count} new profiles in {elapsed/60:.1f} minutes")
        print(f"📊 Total profiles: {len(self.profiles)}")
    
    def run(self):
        """Main execution flow"""
        print("🚀 GitHub Ukrainian Developers Scraper")
        print("=" * 50)
        
        # Load existing progress
        self.load_checkpoint()
        
        # Search for usernames
        usernames = self.search_users()
        
        # Fetch detailed profiles
        self.scrape_profiles(usernames)
        
        print("\n" + "=" * 50)
        print(f"✅ COMPLETE! Scraped {len(self.profiles)} profiles")
        print(f"📁 Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        scraper = GitHubScraper()
        scraper.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Progress has been saved.")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        raise