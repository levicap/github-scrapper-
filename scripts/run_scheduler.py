#!/usr/bin/env python3
"""
Run Scheduler
Start the scheduler to run all scrapers on schedule
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scheduler import main

if __name__ == "__main__":
    main()
