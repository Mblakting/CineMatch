# -*- coding: utf-8 -*-
"""
Configuration for CineMatch.
"""

import os

# API Configuration
API_KEY = os.getenv("TMDB_API_KEY", "244a292fb73be77c0134ac3de3c9b824")

# UI Settings
UI_CONFIG = {
    'app_title': 'CineMatch',
    'default_search': '',
    'default_min_year': 1990,
    'default_min_rating': 5.0
}

# Recommendation Settings
RECOMMENDATION_CONFIG = {
    'default_n': 12,
    'candidate_pool': 28,
    'tmdb_pool': 20,
    'live_cache_ttl': 300
}
