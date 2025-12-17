#!/usr/bin/env python3
"""
GitHub Profile Scraper - Database Version
Reads usernames from database and saves profiles directly to PostgreSQL.
"""

import os
import time
from datetime import datetime
from github import Github, RateLimitExceededException, Auth
from dotenv import load_dotenv
from dbutils import DatabaseManager

# Load environment variables
load_dotenv()

# Configuration
TARGET_PROFILES = 10000
CHECKPOINT_INTERVAL = 50


class ProfileScraper:
    """Scrape detailed GitHub profiles"""
    
    def __init__(self):
        self.tokens = self._load_tokens()
        self.current_token_index = 0
        auth = Auth.Token(self.tokens[0])
        self.github = Github(auth=auth)
        self.db = DatabaseManager()
        
    def _load_tokens(self):
        """Load GitHub tokens from environment"""
        tokens = []
        for i in range(1, 10):
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
    
    def _extract_social_links(self, user):
        """Extract all social media links from profile"""
        import re
        
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
        """Fetch detailed profile information for a user"""
        try:
            user = self.github.get_user(username)
            social_links = self._extract_social_links(user)
            
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
                'top_repos': top_repos,
                'scraped_at': datetime.utcnow().isoformat()
            }
            
            return profile
        
        except Exception as e:
            print(f"❌ Failed to fetch {username}: {e}")
            return None
    
    def scrape_profiles(self):
        """Fetch detailed profiles for all usernames in database"""
        print(f"\n👤 Fetching profiles from database...")
        print("=" * 60)
        
        total_profiles = self.db.get_developer_count()
        print(f"📊 Already scraped: {total_profiles} profiles")
        
        if total_profiles >= TARGET_PROFILES:
            print(f"✅ Already reached target of {TARGET_PROFILES} profiles!")
            return
        
        all_usernames = self.db.get_usernames()
        print(f"📋 Total usernames available: {len(all_usernames)}")
        
        scraped_usernames = self.db.get_scraped_usernames()
        remaining = set(all_usernames) - scraped_usernames
        print(f"⏳ Remaining to scrape: {len(remaining)}")
        
        start_time = time.time()
        count = 0
        
        for username in remaining:
            total_profiles = self.db.get_developer_count()
            if total_profiles >= TARGET_PROFILES:
                print(f"\n🎯 Target reached: {TARGET_PROFILES} profiles!")
                break
            
            try:
                profile = self.fetch_profile(username)
                
                if profile:
                    developer_id = self.db.insert_developer(profile)
                    
                    if developer_id:
                        count += 1
                        total_profiles = self.db.get_developer_count()
                        
                        elapsed = time.time() - start_time
                        rate = count / (elapsed / 3600) if elapsed > 0 else 0
                        
                        print(f"  [{total_profiles}/{TARGET_PROFILES}] {username} | Rate: {rate:.1f}/hour")
                        
                        if count % CHECKPOINT_INTERVAL == 0:
                            stats = self.db.get_stats()
                            print(f"  💾 Checkpoint - Total: {stats.get('total_developers', 0)}, With email: {stats.get('developers_with_email', 0)}, With social: {stats.get('developers_with_social', 0)}")
                
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
        
        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        print(f"✅ Scraped {count} new profiles in {elapsed/60:.1f} minutes")
        
        stats = self.db.get_stats()
        print(f"\n📊 Final Statistics:")
        print(f"  Total profiles: {stats.get('total_developers', 0)}")
        print(f"  With email: {stats.get('developers_with_email', 0)}")
        print(f"  With social links: {stats.get('developers_with_social', 0)}")
        print(f"  Average followers: {stats.get('avg_followers', 0)}")
        print(f"  Average repos: {stats.get('avg_repos', 0)}")
    
    def run(self):
        """Main execution flow"""
        try:
            print("🚀 GitHub Profile Scraper - Database Version")
            print("=" * 60)
            
            self.db.connect()
            self.db.create_tables()
            self.scrape_profiles()
            
            print(f"\n✅ COMPLETE!")
            print(f"📁 Data saved to PostgreSQL database")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            raise
        finally:
            self.db.disconnect()


if __name__ == "__main__":
    try:
        scraper = ProfileScraper()
        scraper.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Progress saved to database.")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        raise