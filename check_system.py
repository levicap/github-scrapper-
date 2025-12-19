#!/usr/bin/env python3
"""
System Check Script
Verifies that all dependencies and configuration are correct
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_python_version():
    """Check Python version"""
    print("🐍 Python Version Check...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  ❌ Python {version.major}.{version.minor}.{version.micro} (need 3.8+)")
        return False

def check_dependencies():
    """Check required dependencies"""
    print("\n📦 Dependencies Check...")
    required = ['github', 'dotenv', 'psycopg2', 'apscheduler']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (missing)")
            missing.append(package)
    
    return len(missing) == 0

def check_env_file():
    """Check .env file"""
    print("\n🔧 Environment File Check...")
    env_path = project_root / '.env'
    
    if env_path.exists():
        print("  ✅ .env file exists")
        
        # Check for required variables
        with open(env_path) as f:
            content = f.read()
            
        required_vars = ['GITHUB_TOKEN', 'DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        for var in required_vars:
            if var in content and not content.split(var)[1].split('\n')[0].strip().endswith('_here'):
                print(f"  ✅ {var} configured")
            else:
                print(f"  ⚠️  {var} needs configuration")
        
        return True
    else:
        print("  ❌ .env file not found")
        print("     Run: cp .env.example .env")
        return False

def check_database():
    """Check database connection"""
    print("\n🗄️  Database Connection Check...")
    
    try:
        from src.config import settings
        import psycopg2
        
        config = settings.database.config_dict
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"  ✅ Connected to PostgreSQL")
        print(f"     {version.split(',')[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'developers'")
        if cursor.fetchone()[0] > 0:
            print("  ✅ 'developers' table exists")
        else:
            print("  ⚠️  'developers' table not found (run migration)")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        print("     Make sure PostgreSQL is running:")
        print("     docker compose -f docker/docker-compose.yml up postgres -d")
        return False

def check_github_tokens():
    """Check GitHub tokens"""
    print("\n🔑 GitHub Token Check...")
    
    try:
        from src.config import settings
        
        tokens = settings.github.TOKENS
        print(f"  ✅ {len(tokens)} token(s) loaded")
        
        # Test first token
        from github import Github, Auth
        auth = Auth.Token(tokens[0])
        g = Github(auth=auth)
        user = g.get_user()
        print(f"  ✅ Token valid (authenticated as: {user.login})")
        
        # Check rate limit
        rate_limit = g.get_rate_limit()
        print(f"  ℹ️  Rate limit: {rate_limit.core.remaining}/{rate_limit.core.limit}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ GitHub token error: {e}")
        return False

def check_structure():
    """Check project structure"""
    print("\n📁 Project Structure Check...")
    
    required_paths = [
        'src/config',
        'src/database',
        'src/scrapers',
        'src/utils',
        'docker',
        'scripts'
    ]
    
    all_exist = True
    for path in required_paths:
        full_path = project_root / path
        if full_path.exists():
            print(f"  ✅ {path}/")
        else:
            print(f"  ❌ {path}/ (missing)")
            all_exist = False
    
    return all_exist

def main():
    """Run all checks"""
    print("=" * 70)
    print("🔍 GitHub Scraper System Check")
    print("=" * 70)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Environment File", check_env_file),
        ("Project Structure", check_structure),
        ("Database Connection", check_database),
        ("GitHub Tokens", check_github_tokens)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} check failed with error: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n  {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All checks passed! You're ready to run the scrapers.")
        print("\nNext steps:")
        print("  1. Run migration: python migrate_database.py")
        print("  2. Start scraping: python scripts/run_username_scraper.py")
        print("  3. Or use scheduler: python scripts/run_scheduler.py")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
