"""Configuration settings for the live betting alert system."""

# API Configuration
API_KEY = "9620b5a904bfe764ace4bc327e9fa629"
BASE_URL = "https://v3.football.api-sports.io"

# Analysis Parameters
MIN_MATCHES_REQUIRED = 4
COMBINED_THRESHOLD = 1.5
SCAN_HOURS_AHEAD = 24
REQUEST_DELAY = 1.5  # seconds between API calls

# Output Settings
OUTPUT_DIRECTORY = "betting_alerts"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
