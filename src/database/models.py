"""
Database models and enums
"""
from enum import Enum


class EnrichmentStatus(str, Enum):
    """Enrichment status for GitHub users"""
    INITIAL = "INITIAL"           # Username collected
    PROCESSING = "PROCESSING"     # Currently being processed (claimed)
    PROFILED = "PROFILED"         # GitHub profile fetched
    ENHANCED = "ENHANCED"         # Social media scraped
    FAILED = "FAILED"             # Failed after max retries
    
    def __str__(self):
        return self.value
